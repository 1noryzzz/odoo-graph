# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingFactorRootUserWizard(models.TransientModel):
    _name = 'ifs.partner.factor.root.user.wizard'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建保理方根用户'
