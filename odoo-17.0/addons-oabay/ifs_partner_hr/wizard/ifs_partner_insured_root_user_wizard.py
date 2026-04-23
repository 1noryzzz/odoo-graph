# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsuredRootUserWizard(models.TransientModel):
    _name = 'ifs.partner.insured.root.user.wizard'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建被保人方根用户'
