# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingBaseCompany(models.Model):
    _inherit = 'ifs.base.company'

    #订单
    def view_sub_loan_account_info(self):
        self.ensure_one()
        merchant_id = self.env['ifs.partner.merchant'].search([('ifs_company_id', '=', self.id)])
        if merchant_id:
            return {
                'name': _('订单列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.trade.order',
                'res_id': False,
                'domain': [('merchant_id', '=', merchant_id.id)],
                'target': 'current',
            }
