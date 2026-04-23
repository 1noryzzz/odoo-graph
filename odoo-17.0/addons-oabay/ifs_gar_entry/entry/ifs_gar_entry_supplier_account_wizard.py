# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplierAccountWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.account.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '供应方进件流程--账户信息'
    _ref_model = 'ifs.gar.entry.supplier'

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', required=True, ondelete='restrict', index=True)

    bank_id = fields.Many2one('res.bank', string='开户行', required=True)
    acc_number = fields.Char('账号', required=True)
    deposit_license = fields.Binary(string='开户证可证')

    def action_next(self):
        self.entry_id.write({
            'bank_id': self.bank_id,
            'acc_number': self.acc_number,
            'deposit_license': self.deposit_license,
        })

        return super().action_next()
