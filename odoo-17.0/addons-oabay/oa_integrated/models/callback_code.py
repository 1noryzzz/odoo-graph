# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class OACallbackCode(models.Model):
    _name = 'oa.callback.code'
    _description = "回调类型列表"
    _rec_name = 'name'

    ValueType = [
        ('00', '通讯录事件'),
        ('01', '群会话事件'),
        ('02', '签到事件'),
        ('03', '审批事件'),
        ('04', '考勤事件'),
    ]

    name = fields.Char(string='类型名')
    value = fields.Char(string='类型代码')
    color = fields.Integer(string=u'color')
    value_from = fields.Selection([
        ('unknown', '未定义')], string=u'事件来源', required=True)
    value_type = fields.Selection(
        string=u'事件分类', selection=ValueType, default='')    #TODO: 用事件来源来过滤分类

    _sql_constraints = [
        ('value_uniq', 'unique(value, value_type, value_from)', u'同一来源的类型代码重复!'),
        ('name_uniq', 'unique(name, value_from)', u'同一来源的类型名重复!'),
    ]
