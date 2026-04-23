# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsEntrySupplierSelectorWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.selector.wizard'
    _description = '采购方进件向导'

    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', required=True, domain=lambda self: self._supplier_domain())
    
    def _supplier_domain(self):
        invite_ids = self.env['ifs.gar.invite.merchant'].search([
            ('ifs_company_id.company_id', '=', self.env.company.id)
        ])
        return [
            ('id', 'in', invite_ids.filtered(
                lambda invite: invite.state != 'ready').mapped('supplier_id').ids)
        ]

    def choice_supplier(self):
        return self.env['ifs.gar.invite.merchant'].search([
            ('ifs_company_id.company_id', '=', self.env.company.id),
            ('supplier_id', '=', self.supplier_id.id)
        ]).start_entry()
