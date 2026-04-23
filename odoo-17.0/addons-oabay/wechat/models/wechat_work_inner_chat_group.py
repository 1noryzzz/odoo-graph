# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkInnerChatGroup(models.Model):
    _name = 'wechat.work.inner.chat.group'
    _description = 'Wechat Work Inner Chat Group'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'name'

    name = fields.Char('Group Name', required=True)
    agent_id = fields.Many2one(
        "wechat.work.agent.config", string="Agent Config", ondelete="restrict", required=True)
    owner_user_id = fields.Many2one(
        "wechat.work.user", string="Owner User", ondelete="restrict")
    user_ids = fields.Many2many(
        'wechat.work.user', 'wechat_work_inner_chat_group_user_rel', 'inner_chat_gid', 'uid', required=True)
    chatid = fields.Char('Wechat Work Chat Id', required=True)
    remark = fields.Text('Inner Chat Group Description')
