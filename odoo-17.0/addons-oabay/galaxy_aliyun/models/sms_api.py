# -*- coding: utf-8 -*-

import logging
import json

from odoo.addons.sms.tools import sms_api
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from odoo import _, api, models

_logger = logging.getLogger(__name__)


class SmsApi(models.AbstractModel):
    _name = 'galaxy.aliyun.sms.api'
    _description = '短信发送API'

    def _create_client(self) -> Dysmsapi20170525Client:
        cfg = self.env['ir.config_parameter'].sudo()
        config = open_api_models.Config(
            access_key_id=cfg.get_param('galaxy.aliyun.access.key.id', ''),
            access_key_secret=cfg.get_param(
                'galaxy.aliyun.access.key.secret', ''),
        )
        config.endpoint = cfg.get_param('galaxy.aliyun.sms.endpoint', '')
        return Dysmsapi20170525Client(config)

    @api.model
    def _send_sms(self, numbers, message):
        client = self._create_client()
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers=numbers,
            sign_name='云腾智慧',
            template_code='',
            template_param=message
        )
        runtime = util_models.RuntimeOptions()
        return client.send_sms_with_options(send_sms_request, runtime)

    @api.model
    def _send_sms_batch(self, messages):
        """ Send SMS using IAP in batch mode

        :param messages: list of SMS to send, structured as dict [{
            'res_id':  integer: ID of sms.sms,
            'number':  string: E164 formatted phone number,
            'content': string: content to send
            'code': 
        }]

        :return: return of /iap/sms/1/send controller which is a list of dict [{
            'res_id': integer: ID of sms.sms,
            'state':  string: 'insufficient_credit' or 'wrong_number_format' or 'success',
            'credit': integer: number of credits spent to send this SMS,
        }]

        :raises: normally none
        """
        client = self._create_client()
        number_list = []
        for number in messages:
            number_list.append(str(number.get('number')))
        send_batch_sms_request = dysmsapi_20170525_models.SendBatchSmsRequest(
            phone_number_json = json.dumps(number_list),
            sign_name_json = json.dumps([messages[0].get('sign_name')]),
            template_param_json = json.dumps([json.loads(messages[0].get('content'))]),
            template_code = messages[0].get('code')
        )
        runtime = util_models.RuntimeOptions()
        
        return client.send_batch_sms_with_options(send_batch_sms_request, runtime)

    @api.model
    def _get_sms_api_error_messages(self):
        """ Returns a dict containing the error message to display for every known error 'state'
        resulting from the '_send_sms_batch' method.
        We prefer a dict instead of a message-per-error-state based method so we only call
        the 'get_credits_url' once, to avoid extra RPC calls. """

        buy_credits_url = self.sudo().env['iap.account'].get_credits_url(
            service_name='sms')
        buy_credits = '<a href="%s" target="_blank">%s</a>' % (
            buy_credits_url,
            _('Buy credits.')
        )
        return {
            'unregistered': _("You don't have an eligible IAP account."),
            'insufficient_credit': ' '.join([_('You don\'t have enough credits on your IAP account.'), buy_credits]),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
        }
