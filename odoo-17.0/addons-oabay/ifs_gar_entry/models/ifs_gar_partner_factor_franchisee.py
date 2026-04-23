# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorFranchisee(models.Model):
    _inherit = 'ifs.gar.partner.factor.franchisee'

    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', string='进件', index=True, ondelete='restrict', required=True)
