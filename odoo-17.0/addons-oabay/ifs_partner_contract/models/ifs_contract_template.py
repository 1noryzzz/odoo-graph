# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessDenied, UserError


class InclusiveFinancingContractTemplate(models.Model):
    _inherit = 'ifs.contract.template'
    
    _sql_constraints = [
        ('code_uniq', 'unique (code, factor_id, supplier_id)', '合同模板已存在！')
    ]

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', index=True, ondelete='restrict')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', index=True, ondelete='restrict')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            factor = self.env['ifs.partner.factor'].search([
                ('ifs_company_id.company_id.id', '=', self.env.company.id)
            ], limit=1)
            if factor.exists():
                vals['factor_id'] = factor.id
            return super().create(vals_list)

    def retrieve_by_code(self, code, factor_id=False, supplier_id=False):
        contract_template = False
        if factor_id and supplier_id:
            contract_template = self.env['ifs.contract.template'].search(
                [('code', '=', code), ('factor_id', '=', factor_id), ('supplier_id', '=', supplier_id)], limit=1)
        elif factor_id:
            contract_template = self.env['ifs.contract.template'].search(
                [('code', '=', code), ('factor_id', '=', factor_id)], limit=1)
        contract_template = self.env['ifs.contract.template'].search(
                [('code', '=', code)], limit=1) if not contract_template else contract_template
        return contract_template

    def template_selector_supplier(self):
        factor = self.env['ifs.partner.factor'].search([('company_id', '=', self.env.company.id)])
        if factor:
            return {
                'name': _('选择供应方'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.contract.template.supplier.selector.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_factor_id': factor.id,
                    'default_template_id': self.id,
                }
            }
        else:
            raise AccessDenied(_('仅保理方可复制当前合同模板！'))
    
    def copy_contract_template(self, factor_id, supplier_id):
        template = self.search([
            ('factor_id', '=', factor_id.id),
            ('supplier_id', '=', supplier_id.id)], limit=1)
        if template:
            raise UserError(_('当前供应方已存在相应的进件配置！'))
        new_template = self.copy_data()[0]
        new_template.update({
            'factor_id': factor_id.id,
            'supplier_id': supplier_id.id
        })
        template_id = self.create(new_template)
        return {
            'name': _(f'{template_id.display_name}'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.contract.template',
            'res_id': template_id.id,
            'target': 'current'
        }