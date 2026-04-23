# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields


class InclusiveFinancingPartnerSupplier(models.Model):
    _inherit = 'ifs.partner.supplier'

    sub_loan_account_ids = fields.One2many(
        'ifs.gar.sub.loan.account', 'supplier_id', string='子贷款账户')

    total_quota = fields.Monetary('合作额度', compute='_compute_quota_info')
    approved_quota = fields.Monetary('已批额度', compute='_compute_quota_info')

    @api.depends('factor_ids', 'merchant_ids')
    def _compute_quota_info(self):
        for record in self:
            quota_info = {
                'total_quota': 0.00,
                'approved_quota': 0.00,
            }

            # 注意这里需要通过数据的rule来限制，否则会出现数据泄露
            factor_ids = self.env['ifs.partner.factor'].search(
                [('id', 'in', record.factor_ids.factor_id.ids)])
            quota_info.update({
                'total_quota': reduce(
                    lambda prev, curr: prev + curr, record.factor_ids.filtered(lambda x: x.factor_id.id in factor_ids.ids).mapped('total_quota'), 0.00),
                'approved_quota': reduce(
                    lambda prev, curr: prev + curr, record.sub_loan_account_ids.mapped('approved_quota'), 0.00)
            })

            record.update(quota_info)

    def view_quota_info(self):
        # 这里在合同模块扩展，显示最高额度合同
        pass

    def view_loan_account_info(self):
        # TODO: 跳转到ifs.gar.sub.loan.account 列表
        pass
