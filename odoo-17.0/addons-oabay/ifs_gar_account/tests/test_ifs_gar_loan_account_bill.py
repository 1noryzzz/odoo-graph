# -*- coding: utf-8 -*-

import logging

from datetime import datetime, timedelta
from odoo import _, api, models, fields
from odoo.tests.common import SingleTransactionCase

_logger = logging.getLogger(__name__)


class TestIfsGarLoanAccountBill(SingleTransactionCase):

    def test_00(self):
        user = self.env['res.users'].search([('login', '=', 'ferrenliu@163.com')], limit=1)
        _logger.error(f'Time zone: {user.tz}')
        user = user.with_context(tz='Asia/Shanghai')
        _logger.error(f"Time zone1: {user._context.get('tz')}")
        _logger.error(f'Time zone2: {user.env.user.tz}')
        current_repayment_date = datetime.utcfromtimestamp((
            fields.Datetime.context_timestamp(
                user, datetime.combine(fields.Date.today(), datetime.min.time()))
            + timedelta(hours=4.5)).timestamp())

        _logger.error(f'current_repayment_date: {current_repayment_date.tzname()}')
        
        _logger.error(f'tz: {fields.Datetime.context_timestamp(user, datetime.combine(fields.Date.today(), datetime.min.time())).tzname()}')
        _logger.error(f'tz: {fields.Datetime.context_timestamp(user, datetime.combine(fields.Date.today(), datetime.min.time())).tzname()}')
