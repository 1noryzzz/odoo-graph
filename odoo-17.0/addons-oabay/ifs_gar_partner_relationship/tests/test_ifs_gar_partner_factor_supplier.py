# -*- coding: utf-8 -*-

import logging

from odoo.tests.common import SingleTransactionCase

_logger = logging.getLogger(__name__)

class TestIfsGarPartnerFactorSupplier(SingleTransactionCase):

    def test_00(self):
        supplier = self.env['ifs.partner.supplier'].browse([1]).with_user(
            self.env['res.users'].browse([11])
        )
        _logger.error(f'supplier: {supplier.id}')
        self.assertEqual(1, len(supplier.merchant_ids.ids), "Test factor filltered error.")

