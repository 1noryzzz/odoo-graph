# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SMSTemplatePreview(models.TransientModel):
    _inherit = "sms.template.preview"

    template_body = fields.Char(compute="_compute_sms_template_fields")
    template_param = fields.Char(compute="_compute_sms_template_fields")

    @api.depends('lang', 'resource_ref')
    def _compute_sms_template_fields(self):
        for wizard in self:
            wizard.template_body = wizard.sms_template_id.template_body

            if wizard.sms_template_id and wizard.resource_ref:
                wizard.body = wizard.sms_template_id._render_field(
                    'body', [wizard.resource_ref.id], set_lang=wizard.lang)[wizard.resource_ref.id]
                wizard.template_param = wizard.sms_template_id._render_field(
                    'template_param', [wizard.resource_ref.id], set_lang=wizard.lang)[wizard.resource_ref.id]
            else:
                wizard.body = wizard.sms_template_id.body
                wizard.template_param = wizard.sms_template_id.template_param
