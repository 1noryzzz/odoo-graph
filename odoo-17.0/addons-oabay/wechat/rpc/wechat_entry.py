# coding=utf-8

import logging

from odoo.exceptions import ValidationError
from wechatpy.client import WeChatClient
from wechatpy.crypto import WeChatCrypto

from .entry_base import EntryBase

_logger = logging.getLogger(__name__)

WechatEntryDict = {}


class WechatEntry(EntryBase):
    def __init__(self, dbname, app_id):
        self.client = None
        self.crypto_handle = None
        self.message_token = None
        self.subscribe_auto_msg = None

        super(WechatEntry, self).__init__(dbname, app_id)

    # def upload_media(self, media_type, media_file):
    #     return self.client.media.upload(media_type, media_file)

    # def chat_send(self, uuid, msg):
    #     openid = self.get_openid_from_uuid(uuid)
    #     if openid:
    #         self.client.message.send_text(openid, msg)

    # def send_image(self, uuid, media_id):
    #     openid = self.get_openid_from_uuid(uuid)
    #     if openid:
    #         self.client.message.send_image(openid, media_id)

    # def send_voice(self, uuid, media_id):
    #     openid = self.get_openid_from_uuid(uuid)
    #     if openid:
    #         self.client.message.send_video(openid, media_id)

    # def create_reply(self, ret_msg, message):
    #     if type(ret_msg) == dict:
    #         if ret_msg.get('media_type') == 'news':
    #             self.client.send_articles(message.source, ret_msg['media_id'])
    #         return ret_msg
    #     else:
    #         return ret_msg

    def init(self, env, from_ui=False):
        self.init_data()
        global WechatEntryDict

        entry_name = '-'.join([
            self.dbname, self.app_id
        ])
        if entry_name in WechatEntryDict:
            del WechatEntryDict[entry_name]
        WechatEntryDict[entry_name] = self

        offiaccount = env['wechat.offiaccount.config'].sudo().search(
            [('app_id', '=', self.app_id)], limit=1)

        if offiaccount.exists():
            self.secret = offiaccount.secret
            self.message_token = offiaccount.message_token
            self.message_encoding_aeskey = offiaccount.message_encoding_aeskey
            self.message_encrypt_mode = offiaccount.message_encrypt_mode
            self.message_format = offiaccount.message_format

            # if wb_wechat.action:
            #    self.subscribe_auto_msg = wb_wechat.action.get_wx_reply()

            self.client = WeChatClient(
                self.app_id, self.secret, session=self.gen_session())

            try:
                if self.message_encoding_aeskey:
                    self.crypto_handle = WeChatCrypto(
                        self.message_token, self.message_encoding_aeskey, self.app_id)
            except:
                _logger.error(
                    'Init wechat offiaccount setting error, app_id is %s' % self.app_id)
                if not self.app_id:
                    from_ui = False
                if from_ui:
                    raise ValidationError(
                        'Init wechat offiaccount setting error, app_id is %s' % self.app_id)


def retrieve_wechat_entry(env, app_id):
    entry_name = '-'.join([
        env.cr.dbname, app_id
    ])

    if entry_name not in WechatEntryDict:
        WechatEntry(env.cr.dbname, app_id).init(env)

    return WechatEntryDict[entry_name]
