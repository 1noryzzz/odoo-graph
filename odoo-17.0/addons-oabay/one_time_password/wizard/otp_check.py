# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class OTPCheck(models.TransientModel):
    _name = 'otp.check'
    _description = '动态令牌测试'

    otp_auth_id = fields.Many2one(
        'otp.authentication', required=True, string='动态令牌', readonly=True)
    passwd = fields.Char('当前密码')

    def check_passwd(self):
        self.ensure_one()
        
        self.otp_auth_id.check_passwd(self.passwd)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("动态令牌认证成功"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
