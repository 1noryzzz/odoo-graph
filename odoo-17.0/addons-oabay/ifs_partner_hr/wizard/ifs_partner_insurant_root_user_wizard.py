# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingInsurantRootUserWizard(models.TransientModel):
    _name = 'ifs.partner.insurant.root.user.wizard'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建投保人方根用户'
