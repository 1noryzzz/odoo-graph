# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _inherit = 'ifs.partner.merchant'

    entry_date = fields.Datetime('进件时间', compute='_compute_entry_date')

    @api.depends('supplier_ids')
    def _compute_entry_date(self):
        for record in self:
            record.entry_date = False
            supplier_ids = self.env['ifs.partner.supplier'].search(
                [('id', 'in', record.supplier_ids.supplier_id.ids)])
            supplier_merchant = record.supplier_ids.filtered(
                    lambda x: x.supplier_id.id in supplier_ids.ids)
            if record.supplier_ids and supplier_merchant:
                entry_merchant = self.env['ifs.gar.entry.merchant'].search(
                    [('id', 'in', supplier_merchant.entry_id.ids)])
                record.entry_date = entry_merchant.entry_date if entry_merchant else False
            else:
                record.entry_date = False

    def view_entrys(self):
        return {
            'name': _('进件列表'),
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.entry.merchant',
            'type': 'ir.actions.act_window',
            'domain': [('ifs_company_id', '=', self.ifs_company_id.id)],
            'context': {'default_ifs_company_id': self.ifs_company_id.id},
            'target': 'current',
        }
