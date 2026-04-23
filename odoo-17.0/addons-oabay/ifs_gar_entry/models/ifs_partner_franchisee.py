# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerFranchisee(models.Model):
    _inherit = 'ifs.partner.franchisee'

    entry_date = fields.Datetime('进件时间', compute='_compute_entry_date')

    @api.depends('factor_ids')
    def _compute_entry_date(self):
        for record in self:
            record.entry_date = False
            factor_ids = self.env['ifs.partner.factor'].search(
                [('id', 'in', record.factor_ids.factor_id.ids)])
            if record.factor_ids:
                factor_franchisee = record.factor_ids.filtered(
                    lambda x: x.factor_id.id in factor_ids.ids)
                record.entry_date = factor_franchisee[0].entry_id.entry_date if factor_franchisee else False

    def view_entrys(self):
        return {
            'name': _('进件列表'),
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.entry.franchisee',
            'type': 'ir.actions.act_window',
            'domain': [('ifs_company_id', '=', self.ifs_company_id.id)],
            'context': {'default_ifs_company_id': self.ifs_company_id.id},
            'target': 'current',
        }
