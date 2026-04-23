# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # notification_type = fields.Selection(
    #    selection_add=[('wechat', 'Contact with Wechat')])

    work_user_ids = fields.One2many(
        'wechat.work.user', 'user_id', string='企业微信用户', auto_join=True)

    @classmethod
    def _login_with_login_data(cls, db, login_data):
        ip = request.httprequest.environ['REMOTE_ADDR'] if request else 'n/a'
        open_id = login_data.get('open_id', False)
        try:
            if not open_id:
                raise ValidationError()

            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                with self._assert_can_auth():
                    user = False
                    login_type = login_data.get('login_type', 'wechat')
                    if login_type == 'wechat_offiaccount':
                        if login_data.get('union_id'):
                            user = self.search(
                                ['&', ('partner_id.union_id', '=',
                                       login_data.get('union_id')), ('active', '=', True)],
                                order='share', limit=1)
                            
                        if not user:
                            user = self.search(
                                ['&', ('partner_id.offiaccount_user_ids.offiaccount_id', '=',
                                       login_data.get('offiaccount_id')),
                                 ('partner_id.offiaccount_user_ids.open_id', '=',
                                  open_id), ('active', '=', True)],
                                order='share', limit=1)
                    elif login_type == 'wechat_weapp':
                        user = self.search(
                            ['&', ('partner_id.weapp_user_ids.open_id', '=',
                                   open_id), ('active', '=', True)],
                            order='share', limit=1)
                    elif login_type == 'wechat_work':
                        user_id = login_data.get('user_id', False)
                        work_id = login_data.get('work_id', False)
                        if not user_id or not work_id:
                            raise ValidationError()

                        user = self.search(
                            ['&', ('work_user_ids.work_userid', '=',
                                   user_id), ('work_user_ids.work_id', '=', work_id)],
                            order='share', limit=1)
                    else:
                        # TODO: other login type
                        user = {'id': False}

                    if not user:
                        raise AccessDenied()
                    user = user.with_user(user)
                    user._update_last_login()
        except AccessDenied:
            _logger.info(
                "Login failed for db:%s open_id:%s from %s", db, open_id, ip)
            raise

        _logger.info(
            "Login successful for db:%s open_id:%s from %s", db, open_id, ip)

        return user.id

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        if type(login) == dict:
            uid = cls._login_with_login_data(db, login)
            if uid:
                with cls.pool.cursor() as cr:
                    env = api.Environment(cr, uid, {})
                    visitor_sudo = env['website.visitor']._get_visitor_from_request(
                    )
                    if visitor_sudo:
                        partner = env.user.partner_id
                        partner_visitor = env['website.visitor'].with_context(
                            active_test=False).sudo().search([('partner_id', '=', partner.id)])
                        if partner_visitor and partner_visitor.id != visitor_sudo.id:
                            # Link history to older Visitor and delete the newest
                            visitor_sudo.website_track_ids.write(
                                {'visitor_id': partner_visitor.id})
                            visitor_sudo.unlink()
                            # If archived (most likely by the cron for inactivity reasons), reactivate the partner's visitor
                            if not partner_visitor.active:
                                partner_visitor.write({'active': True})
                        else:
                            vals = {
                                'partner_id': partner.id,
                                'name': partner.name
                            }
                            visitor_sudo.write(vals)
            return uid
        else:
            return super(ResUsers, cls).authenticate(db, login, password, user_agent_env)

    def update_from_wechat_work(self, wechat_work_record):
        self.ensure_one()
        if wechat_work_record.get('status') == 1:
            self.write({
                'active': True,
                'company_ids': [(4, wechat_work_record.get('company_id'))],
            })
            if self.share:
                self.write({
                    'login': wechat_work_record.get('work_userid'),
                    'name': wechat_work_record.get('name'),
                    'notification_type': 'inbox',
                    'groups_id': self._default_groups()
                })
        elif wechat_work_record.get('status') in (2, 3, 4, 5) and self.company_id.id == wechat_work_record.get('company_id'):
            self.write({
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])]
            })
        else:
            self.write({
                'company_ids': [(3, wechat_work_record.get('company_id'))],
            })

    def create_from_wechat_work(self, wechat_work_record):
        return self.create({
            'active': True,
            'login': wechat_work_record.get('work_userid'),
            'name': wechat_work_record.get('name'),
            'company_ids': [(4, wechat_work_record.get('company_id'))],
            'notification_type': 'inbox',
            'groups_id': self._default_groups() if wechat_work_record.get('status') == 1 else [self.env.ref('base.group_portal').id]
        })
