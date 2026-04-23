# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerSupplier(models.Model):
    _name = 'ifs.partner.supplier'
    _description = '供应方基本信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'supplier'
    
    def action_certificate_company(self):
        for record in self:
            record.ifs_company_id.certificate_company()
