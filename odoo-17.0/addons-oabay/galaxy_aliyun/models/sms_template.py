# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class SMSTemplate(models.Model):
    _inherit = "sms.template"
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)', '该短信模板代码已存在！')
    ]

    code = fields.Char('短信模板代码')
    aliyun_code = fields.Char('阿里云模板代码')
    sign_name = fields.Char('短信签名')
    template_type = fields.Selection([
        ('0', '验证码'),
        ('1', '短信通知'),
        ('2', '推广短信'),
        ('3', '国际/港澳台消息'),
    ], string='短信类型')
    state = fields.Selection([
        ('0', '审核中'),
        ('1', '审核通过'),
        ('2', '审核失败,请在返回参数Reason中查看审核失败原因'),
        ('10', '取消审核'),
    ], string='模板审核状态')
