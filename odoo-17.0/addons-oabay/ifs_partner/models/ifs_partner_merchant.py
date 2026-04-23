# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _name = 'ifs.partner.merchant'
    _description = '采购方基本信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'merchant'

    def action_certificate_company(self):
        for record in self:
            record.ifs_company_id.certificate_company()