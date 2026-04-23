# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OACallbackCode(models.Model):
    _inherit = 'oa.callback.code'
    
    ValueType = [
        ('message', '公众号普通消息'),
        ('event', '公众号事件'),
        ('unknown', '未知分类'),
    ]

    value_from = fields.Selection(selection_add=[
        ('wechat', u'微信公众号'), ('wework', u'企业微信')
    ], ondelete={'wechat': 'cascade', 'wework': 'cascade'})
    value_type = fields.Selection(selection_add=ValueType)