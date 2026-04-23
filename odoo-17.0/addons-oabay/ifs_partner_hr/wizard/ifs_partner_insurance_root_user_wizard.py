# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsuranceRootUserWizard(models.TransientModel):
    _name = 'ifs.partner.insurance.root.user.wizard'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建保险公司根用户'
