# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerMerchant(models.Model):
    _inherit = 'ifs.partner.merchant'

    expire_date = fields.Date('合同到期时间', compute='_compute_expire_date')

    @api.depends('supplier_ids')
    def _compute_expire_date(self):
        for record in self:
            record.expire_date = False
            supplier_ids = self.env['ifs.partner.supplier'].search(
                [('id', 'in', record.supplier_ids.supplier_id.ids)])
            supplier_merchant = record.supplier_ids.filtered(
                    lambda x: x.supplier_id.id in supplier_ids.ids)
            if record.supplier_ids:
                record.expire_date = supplier_merchant[0].t18_contract_info_id.expire_date if supplier_merchant else False

    def view_contract_info(self):
        entry_merchant = ['ifs.gar.entry.merchant,' + str(entry_id) for entry_id in self.supplier_ids.filtered(
            lambda fs: fs.factor_id.company_id.id == self.env.company.id or fs.supplier_id.company_id.id == self.env.company.id).mapped('entry_id').ids] + ['ifs.partner.merchant,' + str(self.id)]
        return {
                'name': _('合同查看'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.contract.info',
                'views': [
                    [self.env.ref('ifs_contract.ifs_contract_info_view_tree').id, 'tree'],
                    [self.env.ref('ifs_contract.ifs_contract_info_view_form_detail').id, 'form']
                ],
                'res_id': False,
                'target': 'current',
                'domain': ['|', '|', ('partner_one', 'in', entry_merchant), ('partner_two', 'in', entry_merchant), ('partner_three', 'in', entry_merchant)],
            }
