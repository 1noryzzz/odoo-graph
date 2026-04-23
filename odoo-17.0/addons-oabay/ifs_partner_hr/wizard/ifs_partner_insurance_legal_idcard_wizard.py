# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsuranceLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.insurance.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新保险公司法人身份证'
