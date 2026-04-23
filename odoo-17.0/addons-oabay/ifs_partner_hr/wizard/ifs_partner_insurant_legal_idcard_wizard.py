# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsurantLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.insurant.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新投保人方法人身份证'
