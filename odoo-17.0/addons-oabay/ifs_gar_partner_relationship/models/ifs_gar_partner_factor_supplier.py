# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorSupplier(models.Model):
    _name = 'ifs.gar.partner.factor.supplier'
    _description = '保理方与供应方关联关系'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_constraints = [(
        'same_factor_id_supplier_id_uniq', 'unique (factor_id, supplier_id)', '保理方与供应方合作记录已存在！')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.supplier_id.name))

        return result

    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', index=True, ondelete='restrict', required=True)
    franchisee_id = fields.Many2one(
        'ifs.partner.franchisee',
        string='合伙人', ondelete='restrict')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier',
        string='供应方', index=True, ondelete='restrict', required=True)
    product_scope = fields.Text('提供的产品/服务', required=True)
