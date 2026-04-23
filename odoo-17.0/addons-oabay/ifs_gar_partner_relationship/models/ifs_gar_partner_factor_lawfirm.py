# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorLawFirm(models.Model):
    _name = 'ifs.gar.partner.factor.lawfirm'
    _description = '保理方与律师事务所关联关系'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_constraints = [
        ('same_factor_id_lawfirm_id_uniq',
         'unique (factor_id, lawfirm_id)', '保理方与该律师事务所合作记录已存在！')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.lawfirm_id.name))

        return result

    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', index=True, ondelete='restrict', required=True)
    lawfirm_id = fields.Many2one(
        'ifs.partner.lawfirm',
        string='律师事务所', index=True, ondelete='restrict', required=True)
