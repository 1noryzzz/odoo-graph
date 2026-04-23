# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models

logger = logging.getLogger(__name__)


class WechatUserMixin(models.AbstractModel):
    _name = 'wechat.user.mixin'
    _description = 'Wechat User Mixin'
    _inherits = {'res.partner': 'partner_id'}

    name = fields.Char(related='partner_id.name',
                       string='Name', inherited=True)
    nickname = fields.Char('Nick Name')

    open_id = fields.Char('OpenId', required=True, index=True, readonly=True)
    avatar_url = fields.Char('Avatar Url')

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', auto_join=True,
                                 string='Related Partner', help='Partner-related data of the user')
    address_ids = fields.One2many(
        'res.partner', compute='_compute_address_ids', string='Delivery Address')

    @api.depends('partner_id')
    def _compute_address_ids(self):
        for weapp_user in self:
            weapp_user.address_ids = weapp_user.partner_id.child_ids.filtered(
                lambda pt: pt.type == 'delivery')


class WechatConfigMultiMixin(models.AbstractModel):
    _name = 'wechat.config.mixin'
    _description = 'Wechat Config Mixin'
    _order = 'is_default desc, name'

    name = fields.Char('名称', required=True)
    app_id = fields.Char('开发者ID', required=True)
    secret = fields.Char('开发者密码', required=True)
    website_id = fields.Many2one(
        "website", string="关联网站", ondelete="restrict", required=True)
    is_default = fields.Boolean("默认公众号", default=False)
    message_handler_url = fields.Char(
        '消息服务地址', readonly=True, compute='_compute_message_handler_url')
    message_token = fields.Char('令牌', required=True)
    message_encoding_aeskey = fields.Char('消息加解密密钥')
    message_encrypt_mode = fields.Selection(
        string="消息加解密方式",
        selection=[
            ('plain', '明文模式'),
            ('mixing', '兼容模式'),
            ('cipher', '安全模式'),
        ], default='mixing', required=True
    )
    message_format = fields.Selection(
        string="消息格式",
        selection=[
            ('xml', 'xml'),
            ('json', 'json'),
        ], default='xml', required=True
    )

    @api.depends('website_id', 'app_id')
    def _compute_message_handler_url(self):
        for config in self:
            owner_website = self.env['website'].sudo(
            ).browse(config.website_id.id)
            if owner_website.exists():
                config.message_handler_url = '%s/wechat/%s/handle_message' % (
                    owner_website.domain, config.app_id)
            else:
                config.message_handler_url = 'No enabled'

