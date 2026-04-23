# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerInsurance(models.Model):
    _name = 'ifs.partner.insurance'
    _description = '保险公司信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'insurance'

    # seal = fields.Binary('保险公司印章图片')

    @api.model_create_multi
    def create(self, vals_list):
        insurances = super().create(vals_list)
        for insurance in insurances:
            insurance.ifs_company_id.active_ifs_partner(insurance._ifs_partner)

        return insurances
