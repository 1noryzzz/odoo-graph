# -*- coding: utf-8 -*-

from odoo.http import Controller, request, route
from odoo import api, registry, SUPERUSER_ID
import json
import logging

_logger = logging.getLogger(__name__)

class PartnerAutocomplete(Controller):
    
    
    @route(['/autocomplete/get_token'], type='json', auth="user", cors="*", methods=['POST'])
    def get_token(self,):
        return "880bee9d-f02d-4ab4-bb1f-89d34a03f03f"

    def get_autocomplete_contact(self, keyword):
        try:
            resp_data = request.env['galaxy.external.api'].invoke(
                'TYC-QYLXFS',
                query={
                    'keyword': keyword,
                },
            )
            req_id = resp_data.id
            with registry(request.env.cr.dbname).cursor() as new_cr:
                new_env = api.Environment(new_cr, SUPERUSER_ID, {})
                raw = new_env['galaxy.external.api.request'].browse(req_id).response_raw

            data = json.loads(raw)
            if data.get('error_code') == 0:
                result = data.get('result', {})
                return {
                    'phone': result.get('phoneNumber'),
                    'email': result.get('email'),
                    'street': result.get('regLocation'),
                }
        except Exception as e:
            _logger.exception(f"get_autocomplete_contact error: {e}")
            return {}
        return {}

    @route(['/autocomplete/contact'], type='json', auth="user", cors="*", methods=['POST'])
    def get_token(self, keyword):
        return self.get_autocomplete_contact(keyword)

    @route(
        ['/openapi/autocomplete/contact', '/openapi/miniapp/autocomplete/contact'],
        type='json',
        auth="openapi",
        cors="*",
        methods=['POST', 'OPTIONS'],
    )
    def get_openapi_autocomplete_contact(self, keyword):
        return self.get_autocomplete_contact(keyword)
