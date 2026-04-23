# -*- coding: utf-8 -*-

import json
from odoo import api, fields, models
from wechatpy.crypto import WeChatWxaCrypto


class WeappSessionWizard(models.TransientModel):

    _name = 'wechat.weapp.session.wizard'
    _description = 'Weapp SessionKey'
    _transient_max_hours = 24

    session_key = fields.Char('session_key', required=True)
    open_id = fields.Char('open_id', required=True)
    weapp_id = fields.Many2one(
        'wechat.weapp.config', required=True, string='Wechat Weapp', ondelete='cascade')
    user_info = fields.Text('User Info')
    phone_info = fields.Text('Phone Info')

    @api.model
    def update_when_login(self, login_data):
        if 'session_key' in login_data and 'weapp_id' in login_data:
            session_wizard = self.search(
                ['&', ('open_id', '=', login_data.get('open_id')),
                 ('weapp_id', '=', login_data.get('weapp_id'))], limit=1)
            if session_wizard.exists():
                session_wizard.write({
                    'session_key': login_data.get('session_key'),
                })
            else:
                self.create({
                    'open_id': login_data.get('open_id'),
                    'session_key': login_data.get('session_key'),
                    'weapp_id': login_data.get('weapp_id')
                })
            self.env.cr.commit()

    @api.model
    def cache_user_info(self, open_id, weapp_id, app_id, iv, encryptedData):
        session_wizard = self.search(
            ['&', ('open_id', '=', open_id),
             ('weapp_id', '=', weapp_id)], limit=1)

        if session_wizard.exists():
            wxa_crypto = WeChatWxaCrypto(
                session_wizard.session_key, iv, app_id)

            session_wizard.update({
                'user_info': json.dumps(wxa_crypto.decrypt_message(encryptedData))
            })
        return session_wizard

    @api.model
    def cache_phone_info(self, open_id, weapp_id, app_id, iv, encryptedData):
        session_wizard = self.search(
            ['&', ('open_id', '=', open_id),
             ('weapp_id', '=', weapp_id)], limit=1)

        if session_wizard.exists():
            wxa_crypto = WeChatWxaCrypto(
                session_wizard.session_key, iv, app_id)

            session_wizard.update({
                'phone_info': json.dumps(wxa_crypto.decrypt_message(encryptedData))
            })
        return session_wizard
