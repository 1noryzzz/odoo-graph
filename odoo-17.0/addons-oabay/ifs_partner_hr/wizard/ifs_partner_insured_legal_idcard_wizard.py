# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsuredLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.insured.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新被保人方法人身份证'
