# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerInsurant(models.Model):
    _name = 'ifs.partner.insurant'
    _description = '投保人方信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'insurant'

    @api.model_create_multi
    def create(self, vals_list):
        insurants = super().create(vals_list)
        for insurant in insurants:
            insurant.ifs_company_id.active_ifs_partner(insurant._ifs_partner)

        return insurants