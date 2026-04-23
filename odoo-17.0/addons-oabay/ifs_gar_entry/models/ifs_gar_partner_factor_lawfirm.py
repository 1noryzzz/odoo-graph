# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorLawfirm(models.Model):
    _inherit = 'ifs.gar.partner.factor.lawfirm'

    entry_id = fields.Many2one(
        'ifs.gar.entry.lawfirm', string='进件', index=True, ondelete='restrict', required=True)
