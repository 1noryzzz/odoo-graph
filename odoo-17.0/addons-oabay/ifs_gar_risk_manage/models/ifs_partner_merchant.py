# -*- coding: utf-8 -*-


from odoo import _, api, fields, models


class InclusiveFinancingPartnerMerchant(models.Model):
    _name = 'ifs.partner.merchant'
    _inherit = ['ifs.partner.merchant', 'ifs.partner.details.mixin']