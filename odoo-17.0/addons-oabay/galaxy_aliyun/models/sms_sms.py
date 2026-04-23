# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    ALIYUN_TO_SMS_STATE = {
        'success': 'sent',
        'isv.OUT_OF_SERVICE': 'sms_credit',
        'isv.MOBILE_NUMBER_ILLEGAL': 'sms_number_format',
        'isp.SYSTEM_ERROR': 'sms_server',
        'isv.ACCOUNT_NOT_EXISTS': 'sms_acc'
    }

    code = fields.Char('短信模板代码',  related="template_id.aliyun_code")
    sign_name = fields.Char(
        '短信签名', help='需使用已经过平台审核的签名', related="template_id.sign_name")

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        aliyun_data = [{
            'res_id': record.id,
            'number': record.number,
            'content': record.body_param,
            'code': record.code,
            'sign_name': record.sign_name
        } for record in self]

        try:
            aliyun_result = self.env['galaxy.aliyun.sms.api']._send_sms_batch(aliyun_data)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(
                self.ids), self.ids, e)
            if raise_exception:
                raise
            self._postprocess_aliyun_sent_sms(
                False,
                aliyun_data,
                unlink_failed=unlink_failed, unlink_sent=unlink_sent)
        else:
            _logger.info('Send batch %s SMS: %s: gave %s',
                         len(self.ids), self.ids, aliyun_result)
            self._postprocess_aliyun_sent_sms(
                aliyun_result, aliyun_data, unlink_failed=unlink_failed, unlink_sent=unlink_sent)

    def _postprocess_aliyun_sent_sms(self, aliyun_result, aliyun_data, failure_reason=None, unlink_failed=False, unlink_sent=True):
        todelete_sms_ids = []
        if unlink_failed and (not aliyun_result or aliyun_result.body.code != 'OK'):
            todelete_sms_ids += [item['res_id'] for item in aliyun_data]
        if unlink_sent and (aliyun_result and aliyun_result.body.code == 'OK'):
            todelete_sms_ids += [item['res_id'] for item in aliyun_data]

        sms_ids = [item['res_id'] for item in aliyun_data]
        if sms_ids:
            if aliyun_result.body.code == 'OK' and not unlink_sent:
                self.env['sms.sms'].sudo().browse(sms_ids).write({
                    'state': 'sent',
                    'failure_type': False,
                })
            if aliyun_result.body.code != 'OK' and not unlink_failed:
                self.env['sms.sms'].sudo().browse(sms_ids).write({
                    'state': 'error',
                    'failure_type': self.ALIYUN_TO_SMS_STATE[aliyun_result.body.code],
                })
            notifications = self.env['mail.notification'].sudo().search([
                ('notification_type', '=', 'sms'),
                ('sms_id', 'in', sms_ids),
                ('notification_status', 'not in', ('sent', 'canceled')),
            ])
            if notifications:
                notifications.write({
                    'notification_status': 'sent' if aliyun_result.body.code == 'OK' else 'exception',
                    'failure_type': self.ALIYUN_TO_SMS_STATE[aliyun_result.body.code] if aliyun_result.body.code != 'OK' else False,
                    'failure_reason': failure_reason if failure_reason else aliyun_result.body.message,
                })

        self.mail_message_id._notify_message_notification_update()
        if todelete_sms_ids:
            self.browse(todelete_sms_ids).sudo().unlink()
