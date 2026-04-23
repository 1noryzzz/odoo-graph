# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorMerchant(models.Model):
    _name = 'ifs.gar.partner.factor.merchant'
    _description = '保理方与采购方关联关系'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_constraints = [
        ('same_factor_id_merchant_id_uniq',
         'unique (factor_id, merchant_id)', '保理方与采购方合作记录已存在！')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.merchant_id.name))

        return result

    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', index=True, ondelete='restrict', required=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant',
        string='采购方', index=True, ondelete='restrict', required=True)
