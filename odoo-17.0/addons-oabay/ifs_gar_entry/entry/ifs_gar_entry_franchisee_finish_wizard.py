# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecEntryFranchiseeFinishWizard(models.TransientModel):
    _name = 'ifs.gar.entry.franchisee.finish.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '合伙人进件流程--进件完成信息'
    _ref_model = 'ifs.gar.entry.franchisee'

    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', required=True, ondelete='restrict', index=True)
    committed = fields.Boolean('是否提交', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['committed'] = True
        return super().create(vals_list)

    def action_next(self):
        self.entry_id.write({
            'state': 'committed',
        })

        return super().action_next()
