# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerSupplierMerchant(models.Model):
    _name = 'ifs.gar.partner.supplier.merchant'
    _description = '供应方与采购方关联关系'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _sql_constraints = [
        ('same_factor_supplier_id_merchant_id_uniq',
         'unique (factor_supplier_id, merchant_id)', '供应方与采购方合作记录已存在！')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.merchant_id.name))

        return result

    factor_supplier_id = fields.Many2one(
        'ifs.gar.partner.factor.supplier', string='保理方与供应方关联关系', index=True, ondelete='restrict', required=True)

    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', related='factor_supplier_id.factor_id', store=True)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier',
        string='供应方', related='factor_supplier_id.supplier_id', store=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant',
        string='采购方', index=True, ondelete='restrict', required=True)
