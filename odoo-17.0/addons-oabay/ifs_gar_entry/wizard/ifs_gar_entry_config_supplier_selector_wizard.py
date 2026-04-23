# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsEntryConfigSupplierSelectorWizard(models.TransientModel):
    _name = 'ifs.gar.entry.config.supplier.selector.wizard'
    _description = '进件配置供应方选择向导'

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', required=True)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', required=True, domain=lambda self: self._supplier_domain())
    
    def _supplier_domain(self):
        factor = self.env['ifs.partner.factor'].search([
            ('company_id', '=', self.env.company.id)
        ])
        return [
            ('id', 'in', factor.supplier_ids.mapped('supplier_id').ids)
        ]

    def choice_supplier(self):
        return self.env['ifs.gar.entry.merchant.config'].copy_entry_config(self.factor_id, self.supplier_id)
