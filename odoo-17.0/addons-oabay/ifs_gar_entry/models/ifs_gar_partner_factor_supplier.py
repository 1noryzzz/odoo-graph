# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorSupplier(models.Model):
    _inherit = 'ifs.gar.partner.factor.supplier'

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', string='进件', index=True, ondelete='restrict', required=True)

    # 这里保留进件时的记录
    # reception_picture = fields.Image('前台照', copy=False)
    # office_area_picture = fields.Image('公司办公区照片', copy=False)
