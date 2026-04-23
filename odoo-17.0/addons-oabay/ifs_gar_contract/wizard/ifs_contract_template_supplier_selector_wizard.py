# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingContractTemplateSupplierSelectorWizard(models.TransientModel):
    _inherit = 'ifs.contract.template.supplier.selector.wizard'

    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', required=True, domain=lambda self: self._supplier_domain())
    
    def _supplier_domain(self):
        factor = self.env['ifs.partner.factor'].search([
            ('company_id', '=', self.env.company.id)
        ])
        return [
            ('id', 'in', factor.supplier_ids.mapped('supplier_id').ids)
        ]
