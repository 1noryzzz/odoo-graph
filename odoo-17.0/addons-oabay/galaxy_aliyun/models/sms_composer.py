# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SendSMS(models.TransientModel):
    _inherit = 'sms.composer'
    
    @api.depends('composition_mode', 'res_model', 'res_id', 'template_id')
    def _compute_body(self):
        for record in self:
            if record.template_id and record.composition_mode == 'comment' and record.res_id:
                record.body = record.template_id._render_field('template_param', [record.res_id], compute_lang=True)[record.res_id]
            elif record.template_id:
                record.body = record.template_id.body
                
    def _action_send_sms_numbers(self):
        self.env['galaxy.aliyun.sms.api']._send_sms_batch([{
            'res_id': 0,
            'number': number,
            'content': self.body,
            'code': self.template_id.code,
            'sign_name': self.template_id.sign_name
        } for number in self.sanitized_numbers.split(',')])
        return True