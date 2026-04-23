# coding=utf-8

import logging

from wechatpy.client import WeChatClient
from wechatpy.crypto import WeChatCrypto

from odoo.exceptions import ValidationError

from .entry_base import EntryBase

_logger = logging.getLogger(__name__)

WeappEntryDict = {}


class WeappEntry(EntryBase):
    def __init__(self, dbname, app_id):
        self.client = None
        self.crypto_handle = None
        self.token = None

        super(WeappEntry, self).__init__(dbname, app_id)

    def init(self, env, from_ui=False):
        self.init_data()
        global WeappEntryDict

        entry_name = '-'.join([
            self.dbname, self.app_id
        ])
        if entry_name in WeappEntryDict:
            del WeappEntryDict[entry_name]
        WeappEntryDict[entry_name] = self

        weapp = env['wechat.weapp.config'].sudo().search(
            [('app_id', '=', self.app_id)], limit=1)

        if weapp.exists():
            self.secret = weapp.secret
            self.message_token = weapp.message_token
            self.message_encoding_aeskey = weapp.message_encoding_aeskey
            self.message_encrypt_mode = weapp.message_encrypt_mode
            self.message_format = weapp.message_format

            self.client = WeChatClient(
                self.app_id, self.secret, session=self.gen_session())

            try:
                if self.message_encoding_aeskey:
                    self.crypto_handle = WeChatCrypto(
                        self.message_token, self.message_encoding_aeskey, self.app_id)
            except:
                _logger.error(
                    'Init weapp setting error, app_id is %s' % self.app_id)
                if not self.app_id:
                    from_ui = False
                if from_ui:
                    raise ValidationError(
                        'Init weapp setting error, app_id is %s' % self.app_id)
        else:
            raise ValidationError(
                'Weapp setting for [%s] is not found!' % self.app_id)


def retrieve_entry(env, app_id):
    entry_name = '-'.join([
        env.cr.dbname, app_id
    ])

    if entry_name not in WeappEntryDict:
        WeappEntry(env.cr.dbname, app_id).init(env)

    return WeappEntryDict[entry_name]
