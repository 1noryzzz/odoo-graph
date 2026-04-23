# -*- coding: utf-8 -*-

from odoo import _, api, models, fields, Command


class InclusiveFinancingPartnerLawfirm(models.Model):
    _inherit = 'ifs.partner.lawfirm'

    expire_date = fields.Date('合同到期时间', compute='_compute_expire_date')

    @api.depends('factor_ids')
    def _compute_expire_date(self):
        for record in self:
            record.expire_date = False
            factor_ids = self.env['ifs.partner.factor'].search(
                [('id', 'in', record.factor_ids.factor_id.ids)])
            factor_lawfirm = record.factor_ids.filtered(
                    lambda x: x.factor_id.id in factor_ids.ids)
            if record.factor_ids:
                record.expire_date = factor_lawfirm[0].p10_contract_info_id.expire_date if factor_lawfirm else False

    def view_contract_info(self):
        entry_lawfirm = ['ifs.gar.entry.lawfirm,' + str(entry_id) for entry_id in self.factor_ids.filtered(
            lambda fs: fs.factor_id.company_id.id == self.env.company.id).mapped('entry_id').ids] + ['ifs.partner.lawfirm,' + str(self.id)]
        return {
            'name': _('合同查看'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ifs.contract.info',
            'res_id': False,
            'target': 'current',
            'domain': [
                '|', '|',
                ('partner_one', 'in', entry_lawfirm),
                ('partner_two', 'in', entry_lawfirm),
                ('partner_three', 'in', entry_lawfirm)
            ],
            'views': [
                [self.env.ref('ifs_contract.ifs_contract_info_view_tree').id, 'tree'],
                [self.env.ref('ifs_contract.ifs_contract_info_view_form_detail').id, 'form']
            ],
        }
