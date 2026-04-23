# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorFranchisee(models.Model):
    _name = 'ifs.gar.partner.factor.franchisee'
    _description = '保理方与合伙人关联关系'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_constraints = [
        ('same_factor_id_franchisee_id_uniq',
         'unique (factor_id, franchisee_id)', '保理方与合伙人合作记录已存在！')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.franchisee_id.name))

        return result

    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', index=True, ondelete='restrict', required=True)
    franchisee_id = fields.Many2one(
        'ifs.partner.franchisee',
        string='合伙人', index=True, ondelete='restrict', required=True)
