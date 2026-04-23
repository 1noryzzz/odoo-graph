# -*- coding: utf-8 -*-

import logging

from cache_base import retrieve_cache_base
from datetime import datetime, timedelta
from odoo import _, api, models, fields, http
from odoo.http import request
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

EXPIRES_IN = 2 * 60 * 60
SAFE_GAP = 300
EXTERNAL_API_METHOD = [
    'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE']


class GalaxyOpenApiApp(models.Model):
    '''
    TODO: 限制应用的访问权限
    '''
    _name = 'galaxy.open.api.app'
    _inherit = ['image.mixin', 'uuid.short.mixin']
    _description = '开放平台第三方应用'

    _sql_constraints = [
        ('app_id_uniq', 'unique (app_id)', '应用ID必须唯一！')
    ]
    _expires_in = EXPIRES_IN

    owner_id = fields.Reference(
        selection=[], string='应用Owner', ondelete='set null')
    company_id = fields.Many2one(
        'res.company', string='公司', required=True, default=lambda self: self.env.company)
    user_id = fields.Many2one(
        'res.users', string='用户', required=True, default=lambda self: self.env.user)

    name = fields.Char(string='应用名称', required=True)
    active = fields.Boolean(string='是否可用', default=True)
    app_id = fields.Char(
        string='应用ID', required=True, copy=False,
        readonly=True, index=True, default=lambda self: ''.join(['go', self.short_uuid4(length=16)]))
    app_secret = fields.Char(
        string='应用密钥', required=True,
        default=lambda self: self.short_uuid4(length=32))

    key_ids = fields.One2many(
        'galaxy.open.api.app.keys', 'api_app_id', string='Keys')
    enable_allow_list = fields.Boolean(string='启用白名单', default=False)
    allow_list = fields.Text(string='IP地址（每行一个）')
    enable_deny_list = fields.Boolean(string='启用黑名单', default=False)
    deny_list = fields.Text(string='IP地址（每行一个）')
    description = fields.Text(string='描述')
    request_method = fields.Selection(
        list(map(lambda item: (item, item), EXTERNAL_API_METHOD)), string='调用方式', tracking=True)
    message_handler_url = fields.Char(string='消息处理地址', required=True)

    @api.onchange('owner_id')
    def _onchange_owner_id(self):
        pass

    def get_access_key(self, sid):
        self.ensure_one()

        last_key = self.env['galaxy.open.api.app.keys'].search([
            ('api_app_id', '=', self.id),
            ('session_id', '=', sid)
        ], limit=1)
        if last_key.id and not last_key.is_invalid:
            current_time = fields.Datetime.now()
            expires_time = last_key.create_date + \
                timedelta(seconds=last_key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining > SAFE_GAP:
                return (False, last_key)

        self.key_ids.filtered(
            lambda key: not (key.force_invalid or key.is_invalid)).invalid_old_keys()
        access_key = self.env['galaxy.open.api.app.keys'].create({
            'api_app_id': self.id,
            'access_token': self.short_uuid4(length=32),
            'session_id': sid,
            'expires_in': self._expires_in,
            'ip': request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        })
        cache_base = retrieve_cache_base(self.env, 'TOKEN-CACHE')
        with cache_base.redis_db.connection_open() as db:
            db.setex(
                name=f'{http.TOKEN_PREFIX}{access_key.access_token}',
                     value=sid, time=access_key.expires_in)

        return (True, access_key)


class GalaxyOpenApiAppKeys(models.Model):
    _name = 'galaxy.open.api.app.keys'
    _description = '开放平台第三方应用的key'
    _order = 'create_date desc'

    api_app_id = fields.Many2one(
        'galaxy.open.api.app', string='应用', index=True, required=True, readonly=True, ondelete="cascade")
    access_token = fields.Char(string='Token', required=True)
    session_id = fields.Char(string='Session ID', required=True)
    expires_in = fields.Integer(string='有效期', required=True)
    force_invalid = fields.Boolean(string='强制失效', default=False)
    is_invalid = fields.Boolean(
        string='已失效', compute='_compute_is_invalid')
    ip = fields.Char(string='IP')

    @api.depends('force_invalid', 'expires_in', 'create_date')
    def _compute_is_invalid(self):
        current_time = fields.Datetime.now()
        for key in self:
            expires_time = key.create_date + \
                timedelta(seconds=key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining <= 0 or key.force_invalid:
                key.is_invalid = True
            else:
                key.is_invalid = False

    @api.autovacuum
    def _gc_invalid_keys(self):
        timeout_ago = datetime.utcnow() - timedelta(seconds=EXPIRES_IN + SAFE_GAP)
        domain = [('create_date', '<', timeout_ago.strftime(
            DEFAULT_SERVER_DATETIME_FORMAT))]
        return self.sudo().search(domain).unlink()

    def invalid_old_keys(self):
        current_time = fields.Datetime.now()
        cache_base = retrieve_cache_base(self.env, 'TOKEN-CACHE')
        for key in self:
            key.force_invalid = True

            expires_time = key.create_date + \
                timedelta(seconds=key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining > SAFE_GAP:
                # 如果Token的有效时间大于300秒，则改为300秒，即5分钟后，此Token失效（留出5分钟给来衔接）
                with cache_base.redis_db.connection_open() as db:
                    session_info = db.get(
                        f'{http.TOKEN_PREFIX}{key.access_token}')
                    if session_info:
                        db.setex(
                            name=f'{http.TOKEN_PREFIX}{key.access_token}', value=session_info, time=SAFE_GAP)
