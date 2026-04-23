# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchant(models.Model):
    _inherit = 'ifs.gar.entry.merchant'

    def confirm_merchant(self):
        merchant = super().confirm_merchant()

        loan_account_sudo = self.env['ifs.gar.loan.account'].sudo()
        factor_merchant_sudo = self.env['ifs.gar.partner.factor.merchant'].sudo(
        )
        supplier_merchant_sudo = self.env['ifs.gar.partner.supplier.merchant'].sudo(
        )

        loan_account = loan_account_sudo.search([
            ('factor_id', '=', self.factor_id.id),
            ('merchant_id', '=', merchant.id),
        ], limit=1)
        if not loan_account.id:
            factor_merchant = factor_merchant_sudo.search([
                ('factor_id', '=', self.factor_id.id),
                ('merchant_id', '=', merchant.id),
            ], limit=1)

            loan_account = loan_account_sudo.create({
                'factor_merchant_id': factor_merchant.id,
                'credit_term': self.credit_term,
                'repay_day': self.repay_day,
            })

            # TODO: 逾期利息计算规则

        supplier_merchant = supplier_merchant_sudo.search([
            ('factor_supplier_id.supplier_id', '=', self.supplier_id.id),
            ('merchant_id', '=', merchant.id),
        ], limit=1)
        self.env['ifs.gar.sub.loan.account'].sudo().create({
            'loan_account_id': loan_account.id,
            'supplier_merchant_id': supplier_merchant.id,
            'approved_quota': self.supplier_final_quota,
        })

        return merchant
