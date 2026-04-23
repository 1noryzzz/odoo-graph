# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingFactorLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.factor.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新保理方法人身份证'
