# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteFranchisee(models.Model):
    _inherit = 'ifs.gar.invite.franchisee'

    p01_contract_info_id = fields.Many2one('ifs.contract.info', string='合伙人合作协议')
    
    can_preview_p01 = fields.Boolean('可预览合同', compute="_compute_can_preview_p01")
    
    @api.depends('state')
    def _compute_can_preview_p01(self):
        for record in self:
            record.can_preview_p01 = (
                record.factor_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended', 'waiting'])

    def draft_contract_p01(self):
        if self.can_preview_p01:
            if not self.p01_contract_info_id.exists():
                template_id = self.env['ifs.contract.template'].retrieve_by_code('P01', self.factor_id.id)
                self.p01_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                    'name': template_id.name,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self._name, self.id),
                    'partner_one_signature': False,
                    'partner_two_signature': self.factor_id.signature,
                    'template_id': template_id.id,
                    'params': json.dumps({
                        'franchisee_type_value': '11111',
                        'franchisee_type': '1111',
                        'province': str('广东省').replace('省', '').replace('市', ''),
                        'city': str('深圳市').replace('市', ''),
                        'area_agency_fee': '11111',
                        'first_year_base_service_fee': '11111%',
                        'first_year_trade_service_fee': '11111%',
                        'follow_up_base_service_fee': '11111%',
                        'follow_up_trade_service_fee': '11111%',
                    }),
                })
            return {
                'name': _('合伙人合作协议预览'),
                'type': 'ir.actions.act_window',
                'res_model': 'ifs.contract.info',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.p01_contract_info_id.id,
            }
