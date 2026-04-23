# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteSupplier(models.Model):
    _inherit = 'ifs.gar.invite.supplier'

    t17_contract_info_id = fields.Many2one('ifs.contract.info', string='总额度合同')
    
    can_preview_t17 = fields.Boolean('可预览合同', compute="_compute_can_preview_t17")
    
    @api.depends('state', 't17_contract_info_id')
    def _compute_can_preview_t17(self):
        for record in self:
            has_permission = self.env.user.has_group('ifs_partner.group_ifs_partner_factor_manager')
            record.can_preview_t17 = (
                has_permission and record.factor_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended', 'waiting']) or (
                    not has_permission and record.create_uid.id == self.env.user.id and record.t17_contract_info_id)

    def write(self, vals):
        res = super().write(vals)

        if 'fee_solution_id' in vals and self.t17_contract_info_id.id:
            self.t17_contract_info_id.write({
                'params': json.dumps({
                    'product_scope': '等待供应方进件后填写',
                    'contract_total_quota': 10000,
                    'fee_solution_contract_content': self.fee_solution_id.contract_content,
                }),
            })

        return res

    def draft_contract_t17(self):
        if self.can_preview_t17:
            if not self.t17_contract_info_id.exists():
                if not self.fee_solution_id.id:
                    raise AccessDenied(_('请先选择收费方案'))

                template_id = self.env['ifs.contract.template'].retrieve_by_code('T17', self.factor_id.id)
                self.t17_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                    'name': template_id.name,
                    'partner_one': '%s,%d' % (self._name, self.id),
                    'partner_two': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_one_signature': False,
                    'partner_two_signature': self.factor_id.signature,
                    'template_id': template_id.id,
                    'params': json.dumps({
                        'product_scope': '等待供应方进件后填写',
                        'contract_total_quota': 10000,
                        'fee_solution_contract_content': self.fee_solution_id.contract_content,
                    }),
                })
            return {
                'name': _('总额度合同预览'),
                'type': 'ir.actions.act_window',
                'res_model': 'ifs.contract.info',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.t17_contract_info_id.id,
            }
