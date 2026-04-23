# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _name = 'sms.sms'
    _inherit = ['sms.sms', 'mail.thread']

    def _sms_get_number_fields(self):
        return ['number']

    template_id = fields.Many2one('sms.template', string='短信模板')
    resource_ref = fields.Reference(
        selection=[], string='短信内容引用模型', ondelete='set null')
    body_param = fields.Text()

    def send(self, unlink_failed=False, unlink_sent=True, auto_commit=False, raise_exception=False):
        for record in self:
            if not record.number and record.partner_id:
                record.number = record.partner_id.phone
            if record.template_id:
                record.write({
                    'body': record.template_id._render_field('template_body', record.ids)[record.id],
                    'body_param': record.template_id._render_field('template_param', record.ids)[record.id],
                })

        super().send(unlink_failed, unlink_sent, auto_commit, raise_exception)
