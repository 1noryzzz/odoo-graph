# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryFranchiseeCoverWizard(models.TransientModel):
    _name = 'ifs.gar.entry.franchisee.cover.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '合伙人进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.franchisee'

    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', required=True, ondelete='restrict', index=True)
