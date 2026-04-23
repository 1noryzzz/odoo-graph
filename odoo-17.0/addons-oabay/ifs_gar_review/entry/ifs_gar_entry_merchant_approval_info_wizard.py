# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantApprWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.approval.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--确认开通'
    _ref_model = 'ifs.gar.entry.merchant'
    _transient_max_hours = 840

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='entry_id.currency_id')
    supplier_final_quota = fields.Monetary(
        '最终额度', related='entry_id.supplier_final_quota')

    def action_sign(self):
        merchant = self.entry_id.confirm_merchant()

        self.entry_id.write({
            'state': 'signed',
            'merchant_id': merchant.id,
        })

        return {
            'name': '采购方开通成功',
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '采购方开通成功',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url':  '/web'
                }
            }
        }
