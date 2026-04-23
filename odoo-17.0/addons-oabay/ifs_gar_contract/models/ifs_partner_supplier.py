# -*- coding: utf-8 -*-

from odoo import _, api, models, fields, Command


class InclusiveFinancingPartnerSupplier(models.Model):
    _inherit = 'ifs.partner.supplier'

    expire_date = fields.Date('合同到期时间', compute='_compute_expire_date')

    @api.depends('factor_ids')
    def _compute_expire_date(self):
        for record in self:
            record.expire_date = False
            factor_ids = self.env['ifs.partner.factor'].search(
                [('id', 'in', record.factor_ids.factor_id.ids)])
            factor_supplier = record.factor_ids.filtered(
                    lambda x: x.factor_id.id in factor_ids.ids)
            if record.factor_ids:
                record.expire_date = factor_supplier[0].t17_contract_info_id.expire_date if factor_supplier else False

    def view_quota_info(self):
        if self.factor_ids.exists():
            factor_supplier = self.factor_ids[0]
            return {
                'name': f'合同详情-{factor_supplier.t17_contract_info_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'ifs.contract.info',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('ifs_contract.ifs_contract_info_view_form_detail').id,
                'res_id': factor_supplier.t17_contract_info_id.id,
            }
        else:
            pass

    def view_contract_info(self):
        entry_supplier = ['ifs.gar.entry.supplier,' + str(entry_id) for entry_id in self.factor_ids.filtered(
            lambda fs: fs.factor_id.company_id.id == self.env.company.id).mapped('entry_id').ids] + ['ifs.partner.supplier,' + str(self.id)]
        return {
            'name': _('合同查看'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ifs.contract.info',
            'res_id': False,
            'target': 'current',
            'domain': [
                '|', '|',
                ('partner_one', 'in', entry_supplier),
                ('partner_two', 'in', entry_supplier),
                ('partner_three', 'in', entry_supplier)
            ],
            'views': [
                [self.env.ref('ifs_contract.ifs_contract_info_view_tree').id, 'tree'],
                [self.env.ref('ifs_contract.ifs_contract_info_view_form_detail').id, 'form']
            ],
        }
