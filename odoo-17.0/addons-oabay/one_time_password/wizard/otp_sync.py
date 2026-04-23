# -*- coding: utf-8 -*-

from odoo import _, fields, models


class OTPSync(models.TransientModel):
    _name = 'otp.sync'
    _description = '动态令牌同步'

    otp_auth_id = fields.Many2one(
        'otp.authentication', required=True, string='动态令牌', readonly=True)
    passwd1 = fields.Char('密码一')
    passwd2 = fields.Char('密码二')

    def otp_sync(self):
        self.ensure_one()

        self.otp_auth_id.sync(self.passwd1, self.passwd2)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("动态令牌同步成功"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
