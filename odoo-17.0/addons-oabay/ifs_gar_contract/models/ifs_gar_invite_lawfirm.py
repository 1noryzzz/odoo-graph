# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteLawfirm(models.Model):
    _inherit = 'ifs.gar.invite.lawfirm'

    p10_contract_info_id = fields.Many2one('ifs.contract.info', string='保理方与律师事务所合作框架协议')
    
    can_preview_p10 = fields.Boolean('可预览合同', compute="_compute_can_preview_p10")
    
    @api.depends('state')
    def _compute_can_preview_p10(self):
        for record in self:
            record.can_preview_p10 = (
                record.factor_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended', 'waiting'])

    def draft_contract_p10(self):
        if self.can_preview_p10:
            if not self.p10_contract_info_id.exists():
                template_id = self.env['ifs.contract.template'].retrieve_by_code('P10', self.factor_id.id)
                self.p10_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                    'name': template_id.name,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self._name, self.id),
                    'partner_one_signature': self.factor_id.signature,
                    'partner_two_signature': False,
                    'template_id': template_id.id,
                })
            return {
                'name': _('保理方与律师事务所合作框架协议预览'),
                'type': 'ir.actions.act_window',
                'res_model': 'ifs.contract.info',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.p10_contract_info_id.id,
            }
