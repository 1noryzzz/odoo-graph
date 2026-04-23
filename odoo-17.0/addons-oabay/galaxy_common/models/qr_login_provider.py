# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class QrLoginProvider(models.Model):
    _name = 'qr.login.provider'
    _description = 'Qr Login Provider'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char('Provider Name', required=True)
    app_id = fields.Char('AppId', required=True)
    secret = fields.Char('Secret', required=True)
    redirect_uri = fields.Char('Redirect Uri')
    scope = fields.Char('Scope')
    enabled = fields.Boolean(string='Allowed')
    css_class = fields.Char(
        string='CSS class', default='fa fa-fw fa-sign-in text-primary')
    body = fields.Char(
        required=True, help='Link text in Login Dialog', translate=True)
    sequence = fields.Integer(default=10)
    is_binded = fields.Boolean(
        'Is Binded', compute='_compute_is_binded', store=True)
    website_id = fields.Many2one(
        "website", string="登录网站", ondelete="restrict", required=True)

    def _compute_is_binded(self):
        for p in self:
            p.is_binded = False


class QrLoginProviderMixin(models.AbstractModel):
    _name = 'qr.login.provider.mixin'
    _description = '二维码配置插件'

    qr_login_id = fields.Many2one(
        "qr.login.provider", string=u"扫码登录配置", ondelete="restrict",
        domain="['|', ('is_binded', '=', False), ('id', '=', qr_login_id)]")
