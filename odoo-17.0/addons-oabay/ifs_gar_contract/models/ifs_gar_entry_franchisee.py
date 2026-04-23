# -*- coding: utf-8 -*-

import json
from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryFranchisee(models.Model):
    _inherit = 'ifs.gar.entry.franchisee'

    def _step_models(self):
        return [
            'ifs.gar.entry.franchisee.cover.wizard',
            'ifs.gar.entry.franchisee.base.info.wizard',
            'ifs.gar.entry.franchisee.contact.wizard',
            'ifs.gar.entry.franchisee.account.wizard',
            'ifs.gar.entry.franchisee.doc.wizard',
            'ifs.gar.entry.franchisee.contract.wizard',
            'ifs.gar.entry.franchisee.finish.wizard',
        ]

    p01_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='事业合伙人合作协议')
    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书托管协议')
    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='CMCA数字证书订户协议')

    p01_contract_name = fields.Char(
        '合伙人合作协议', related='p01_contract_info_id.name', readonly=True)
    p01_contract_pdf = fields.Binary(related='p01_contract_info_id.contract')
    p01_contract_state = fields.Selection(related='p01_contract_info_id.state')
    p01_contract_preview = fields.Binary(related='p01_contract_info_id.contract_preview')

    f42_contract_name = fields.Char(
        '数字证书托管', related='f42_contract_info_id.name', readonly=True)
    f42_contract_pdf = fields.Binary(related='f42_contract_info_id.contract')
    f42_contract_state = fields.Selection(related='f42_contract_info_id.state')
    f42_contract_preview = fields.Binary(related='f42_contract_info_id.contract_preview')

    f43_contract_name = fields.Char(
        '数字证书申请', related='f43_contract_info_id.name', readonly=True)
    f43_contract_pdf = fields.Binary(related='f43_contract_info_id.contract')
    f43_contract_state = fields.Selection(related='f43_contract_info_id.state')
    f43_contract_preview = fields.Binary(related='f43_contract_info_id.contract_preview')

    @api.model_create_multi
    def create(self, vals_list):
        entry_list = super().create(vals_list)
        for entry_id in entry_list:
            f42_template = self.env['ifs.contract.template'].retrieve_by_code('F42', entry_id.invite_id.factor_id.id)
            f43_template = self.env['ifs.contract.template'].retrieve_by_code('F43', entry_id.invite_id.factor_id.id)

            f42_contract = self.env['ifs.contract.info'].create({
                'name': f42_template.name,
                'template_id': f42_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id)
            })
            f43_contract = self.env['ifs.contract.info'].create({
                'name': f43_template.name,
                'template_id': f43_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id)
            })

            entry_id.write({
                'p01_contract_info_id': entry_id.invite_id.p01_contract_info_id.id,
                'f42_contract_info_id': f42_contract.id,
                'f43_contract_info_id': f43_contract.id,
            })
        return entry_list

    def write(self, vals):
        res = super().write(vals)
        if 'email' in vals or 'phone' in vals:
            self.p01_contract_info_id.write({
                'partner_two': '%s,%d' % (self._name, self.id),
            })
            self.f43_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
        elif 'bank_id' in vals or 'acc_number' in vals:
            self.p01_contract_info_id.write({
                'partner_two': '%s,%d' % (self._name, self.id),
            })
        elif 'legal_id_number' in vals:
            self.f42_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
            self.f43_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })

        return res

    def preview_contract(self):
        contract_id = self.env.context.get('contract_id')
        contract_name = self.env.context.get('contract_name')
        return {
            'name': f'合同预览-{contract_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ifs.contract.info',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': contract_id,
        }

    def action_approve(self):
        super().action_approve()

        factor_franchisee = self.env['ifs.gar.partner.factor.franchisee'].search([
            ('entry_id', '=', self.id)], limit=1)
        factor_franchisee.write({
            'p01_contract_info_id': self.p01_contract_info_id.id,
            'f42_contract_info_id': self.f42_contract_info_id.id,
            'f43_contract_info_id': self.f43_contract_info_id.id,
        })
