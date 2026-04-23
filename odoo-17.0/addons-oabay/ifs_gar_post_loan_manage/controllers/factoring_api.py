# -*- coding: utf-8 -*-

from odoo import fields
from odoo.exceptions import UserError
from odoo.http import Controller, request, route


class FactoringApiController(Controller):
    def _ok(self, data=None):
        payload = dict(data or {})
        payload.setdefault('error_msg', '')
        return payload

    def _err(self, message: str, data=None):
        payload = dict(data or {})
        payload['error_msg'] = message
        return payload

    @route(
        ['/factoring_api/query_payment_orders'],
        type='json',
        auth='public',
        methods=['POST'],
        cors='*',
        csrf=False,
    )
    def query_payment_orders(self, project_code=None, request_date=None):
        request_date = request_date or fields.Date.context_today(request.env.user).strftime('%Y-%m-%d')
        data = request.env['ifs.gar.collection.order'].sudo().query_factoring_payment_orders(
            project_code=project_code or '',
            request_date=request_date,
        )
        return self._ok(data)

    @route(
        ['/factoring_api/update_payment_order'],
        type='json',
        auth='public',
        methods=['POST'],
        cors='*',
        csrf=False,
    )
    def update_payment_order(
        self,
        transaction_code=None,
        payment_time=None,
        actual_payment_amount=None,
        payment_voucher=None,
    ):
        if not transaction_code:
            return self._err('transaction_code不能为空')
        if not payment_time:
            return self._err('payment_time不能为空', {'transaction_code': transaction_code})
        if actual_payment_amount is None:
            return self._err('actual_payment_amount不能为空', {'transaction_code': transaction_code})
        try:
            amount = float(actual_payment_amount)
        except (TypeError, ValueError):
            return self._err('actual_payment_amount格式不正确', {'transaction_code': transaction_code})
        if amount < 0:
            return self._err('actual_payment_amount不能小于0', {'transaction_code': transaction_code})

        try:
            data = request.env['ifs.gar.collection.order'].sudo().update_factoring_payment_order(
                transaction_code=transaction_code,
                payment_time=payment_time,
                actual_payment_amount=amount,
                payment_voucher=str(payment_voucher or ''),
            )
            if data.get('error_msg'):
                return self._err(data['error_msg'], {'transaction_code': transaction_code})
            return self._ok(data)
        except UserError as exc:
            return self._err(str(exc), {'transaction_code': transaction_code})
