# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _inherit = 'ifs.partner.merchant'

    loan_account_ids = fields.One2many(
        'ifs.gar.loan.account', 'merchant_id', string='贷款账户')
    sub_loan_account_ids = fields.One2many(
        'ifs.gar.sub.loan.account', 'merchant_id', string='子贷款账户')

    approved_quota = fields.Monetary('授信额度', compute='_compute_quota_info')
    available_quota = fields.Monetary('可用额度', compute='_compute_quota_info')
    freeze_quota = fields.Monetary('冻结额度', compute='_compute_quota_info')
    used_quota = fields.Monetary('已用额度', compute='_compute_quota_info')

    @api.depends('seq_code')
    def _compute_quota_info(self):
        for record in self:
            quota = reduce(lambda prev, curr: {
                'approved_quota': prev.get('approved_quota') + (curr.approved_quota if curr.state == 'normal' else 0.0),
                'freeze_quota': prev.get('freeze_quota') + (curr.freeze_quota if curr.state != 'draft' else 0.0),
                'used_quota': prev.get('used_quota') + (curr.used_quota if curr.state != 'draft' else 0.0),
            }, record.sub_loan_account_ids, {
                'approved_quota': 0.0,
                'freeze_quota': 0.0,
                'used_quota': 0.0,
            })
            quota['available_quota'] = quota.get('approved_quota') - \
                (quota.get('freeze_quota') + quota.get('used_quota'))
            # quota_info = {
            #     'approved_quota': 0.00,
            #     'available_quota': 0.00,
            #     'freeze_quota': 0.00,
            #     'used_quota': 0.00,
            # }

            # # TODO: 注意这里需要通过数据的rule来限制，否则会出现数据泄露
            # quota_info = reduce(
            #     lambda prev, curr: {
            #         'approved_quota': prev['approved_quota'] + curr.approved_quota,
            #         'available_quota': prev['available_quota'] + curr.available_quota,
            #         'freeze_quota': prev['freeze_quota'] + curr.freeze_quota,
            #         'used_quota': prev['used_quota'] + curr.used_quota,
            #     }, record.loan_account_ids, quota_info
            # )

            record.update(quota)

    def view_quota_info(self):
        self.ensure_one()
        return {
            'name': _('贷款账户列表'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.sub.loan.account',
            'res_id': False,
            'domain': [('merchant_id', '=', self.id)],
            'target': 'current',
        }

    def view_sub_loan_account_info(self):
        # TODO: 跳转到账单记录
        pass