# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerInsured(models.Model):
    _name = 'ifs.partner.insured'
    _description = '被保险人方信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'insured'

    @api.model_create_multi
    def create(self, vals_list):
        insureds = super().create(vals_list)
        for insured in insureds:
            insured.ifs_company_id.active_ifs_partner(insured._ifs_partner)

        return insureds
