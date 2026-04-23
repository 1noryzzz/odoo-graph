# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)


class InclusiveFinanchingHrEmployeeCheckcode(models.TransientModel):
    _name = 'ifs.hr.employee.checkcode'
    _description = '验证码'
    _inherit = ['uuid.short.mixin', 'mail.thread']
    
    _template_code = 'HR_SMS_148380455'

    code = fields.Char('验证码')
    phone = fields.Char('手机号')
    template_id = fields.Many2one(
        'sms.template', string='短信模板')

    def _sms_get_number_fields(self):
        return ['phone']

    def send(self, phone, unlink_failed=False, unlink_sent=True, raise_exception=False):
        hr_code = self.create({
            'phone': phone
        })
        res_user = self.env['res.users'].search([('partner_id.phone', '=', phone)])
        res_user.mapped('partner_id').signup_prepare(signup_type="reset", expiration=datetime.now() + timedelta(minutes=3))
        hr_code.code = res_user.partner_id.signup_token
        template = self.env['sms.template'].search([('code', '=', self._template_code)])
        if template:
            params = template._render_field('template_param', [hr_code.id], compute_lang=True)[hr_code.id]
            self.update({
                'template_id': template.id
            })
            aliyun_data = [{
                'res_id': self.id,
                'number': phone,
                'content': params,
                'code': template.aliyun_code,
                'sign_name': template.sign_name
            }]

            try:
                aliyun_result = self.env['sms.api']._send_sms_batch(
                    aliyun_data)
            except Exception as e:
                _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(
                    self.ids), self.ids, e)
                if raise_exception:
                    raise
                self.env['sms.sms']._postprocess_aliyun_sent_sms(
                    False,
                    aliyun_data,
                    unlink_failed=unlink_failed, unlink_sent=unlink_sent)
            else:
                _logger.info('Send batch %s SMS: %s: gave %s',
                             len(self.ids), self.ids, aliyun_result)
                self.env['sms.sms']._postprocess_aliyun_sent_sms(
                    aliyun_result, aliyun_data, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
