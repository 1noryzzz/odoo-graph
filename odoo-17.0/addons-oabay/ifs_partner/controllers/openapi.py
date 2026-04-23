# -*- coding: utf-8 -*-

import logging

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class OpenApiController(Controller):
    @route(['/openapi/supplier/list'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def openapi_supplier_list(self):
        return request.env['ifs.partner.supplier'].search_read(fields=['name', 'seq_code', 'state', 'raw'])

    @route(['/openapi/merchant/list'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def openapi_merchant_list(self):
        return request.env['ifs.partner.merchant'].search_read(fields=['name', 'seq_code', 'state', 'raw'])
