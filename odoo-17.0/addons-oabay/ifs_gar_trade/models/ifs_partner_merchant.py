# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _inherit = 'ifs.partner.merchant'
    
    payment_password = fields.Char('支付密码')

    def start_trade_order(self):
        return self.env['ifs.gar.trade.order'].start_trade_order(self.id)
    
    #订单
    def view_sub_loan_account_info(self):
        self.ensure_one()
        return {
            'name': _('支付订单'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.payment.order',
            'res_id': False,
            'domain': [('merchant_id', '=', self.id)],
            'target': 'current',
        }
