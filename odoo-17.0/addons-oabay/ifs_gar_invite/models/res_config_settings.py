# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_send_sms = fields.Boolean(
        string="是否发送邀请短信", config_parameter='galaxy.aliyun.send.sms', default=False)
    is_send_mail = fields.Boolean(
        string="是否外发邀请邮件", config_parameter='ifs_gar_invite.is_send_mail', default=False)
    email_default_receiver = fields.Char(
        string='默认指定的邀请邮件接收方', config_parameter='ifs_gar_invite.email_default_receiver')
