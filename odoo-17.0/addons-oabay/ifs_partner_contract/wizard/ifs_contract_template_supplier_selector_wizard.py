# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingContractTemplateSupplierSelectorWizard(models.TransientModel):
    _name = 'ifs.contract.template.supplier.selector.wizard'
    _description = '合同模板复制供应方选择向导'

    template_id = fields.Many2one(
        'ifs.contract.template', string='合同模板', required=True)
    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', required=True)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', required=True)

    def choice_supplier(self):
        return self.template_id.copy_contract_template(self.factor_id, self.supplier_id)
