# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvTradeOrderMerchantSelectorWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.merchant.selector.wizard'
    _description = '选择目标企业向导'

    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', domain="[('state', '=', 'normal')]", ondelete='restrict', required=True)
    
    def action_confirm(self):
        self.env['ifs.gar.trade.order'].create({
            'merchant_id': self.merchant_id.id
        }).start_step()