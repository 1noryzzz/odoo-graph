# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerSupplier(models.Model):
    _inherit = 'ifs.partner.supplier'

    invite_merchant_ids = fields.One2many(
        'ifs.gar.invite.merchant', 'supplier_id', string='邀请采购方记录', copy=False)
