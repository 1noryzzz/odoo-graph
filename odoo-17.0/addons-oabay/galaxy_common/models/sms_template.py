# -*- coding: utf-8 -*-

import json

from odoo import _, api, fields, models
from odoo.tools.rendering_tools import parse_inline_template


class SMSTemplate(models.Model):
    _inherit = "sms.template"

    template_body = fields.Char('短信模板', compute='_compute_template_info')
    template_param = fields.Char('短信参数', compute='_compute_template_info')
    template_params_mapping = fields.Char('短信参数映射表')

    @api.depends("body", "template_params_mapping")
    def _compute_template_info(self):
        for sms_template in self:
            sms_template.template_body = ''
            sms_template.template_param = ''
            if sms_template.template_params_mapping:
                param_dict = {}
                
                try:
                    param_mapping = json.loads(sms_template.template_params_mapping)
                    sms_template.template_body = ''
                    for string, expression in parse_inline_template(sms_template.body or ''):
                        sms_template.template_body += string

                        if expression != '':
                            expression = expression.strip()
                            var_name = expression.replace('object.', '')
                            var_name = param_mapping.get(
                                var_name, var_name)
                            param_dict[var_name] = '{{%s}}' % expression

                            sms_template.template_body += ''.join(
                                ['${', var_name, '}'])

                    sms_template.template_param = json.dumps(param_dict)
                except json.decoder.JSONDecodeError:
                    pass
