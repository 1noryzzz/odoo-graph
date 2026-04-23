# coding=utf-8

import logging

from odoo.exceptions import ValidationError
from wechatpy.work.client import WeChatClient
from wechatpy.work.crypto import WeChatCrypto

from .entry_base import EntryBase

_logger = logging.getLogger(__name__)

WorkEntryDict = {}


class WorkEntry(EntryBase):
    def __init__(self, dbname, app_id):
        self.contacts_client = None
        self.clients = {}
        self.crypto_handle = {}
        self.message_token = None

        super(WorkEntry, self).__init__(dbname, app_id)

    def init(self, env, from_ui=False):
        self.init_data()
        global WorkEntryDict

        entry_name = '-'.join([
            self.dbname, self.app_id
        ])
        if entry_name in WorkEntryDict:
            del WorkEntryDict[entry_name]
        WorkEntryDict[entry_name] = self

        wechat_work = env['wechat.work.config'].sudo().search(
            [('corp_id', '=', self.app_id)], limit=1)

        if wechat_work.exists():
            self.secret = wechat_work.corp_contact_secret
            #self.message_token = None
            #self.message_encoding_aeskey = None

            self.contacts_client = WeChatClient(
                self.app_id, self.secret, session=self.gen_session())
            if wechat_work.external_contact_secret:
                self.ext_contacts_client = WeChatClient(
                    self.app_id, wechat_work.external_contact_secret, session=self.gen_session())
            for agent in wechat_work.agent_ids:
                self.clients[agent.agent_id] = WeChatClient(
                    self.app_id, agent.agent_secret, session=self.gen_session())
                try:
                    if agent.message_encoding_aeskey:
                        self.crypto_handle[agent.agent_id] = WeChatCrypto(
                            agent.message_token, agent.message_encoding_aeskey, self.app_id)
                except Exception as e:
                    _logger.error(repr(e))
                    _logger.error(
                        'Init work crypto error, app_id is %s, agent_id is %s' % (self.app_id, agent.agent_id))
        else:
            raise ValidationError(
                'Work setting for [%s] is not found!' % self.app_id)


def retrieve_entry(env, app_id):
    entry_name = '-'.join([
        env.cr.dbname, app_id
    ])

    if entry_name not in WorkEntryDict:
        WorkEntry(env.cr.dbname, app_id).init(env)

    return WorkEntryDict[entry_name]
