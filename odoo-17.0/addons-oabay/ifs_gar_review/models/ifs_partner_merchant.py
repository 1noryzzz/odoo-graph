# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _inherit = 'ifs.partner.merchant'

    approval_date = fields.Datetime('获批时间', compute='_compute_approval_date')

    @api.depends('supplier_ids')
    def _compute_approval_date(self):
        for record in self:
            record.approval_date = False
            supplier_ids = self.env['ifs.partner.supplier'].search(
                [('id', 'in', record.supplier_ids.supplier_id.ids)])
            supplier_merchant = record.supplier_ids.filtered(
                    lambda x: x.supplier_id.id in supplier_ids.ids)
            if record.supplier_ids and supplier_merchant:
                entry_merchant = self.env['ifs.gar.entry.merchant'].search(
                    [('id', 'in', supplier_merchant.entry_id.ids)])
                record.approval_date = entry_merchant.approval_date if entry_merchant else False
            else:
                record.approval_date = False