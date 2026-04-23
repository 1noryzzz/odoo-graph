# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerSupplierMerchant(models.Model):
    _inherit = 'ifs.gar.partner.supplier.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='进件', index=True, ondelete='restrict', required=True)
