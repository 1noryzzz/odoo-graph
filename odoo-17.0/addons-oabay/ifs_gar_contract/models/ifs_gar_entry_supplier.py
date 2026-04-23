# -*- coding: utf-8 -*-

import json
from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplier(models.Model):
    _inherit = 'ifs.gar.entry.supplier'

    def _step_models(self):
        return [
            'ifs.gar.entry.supplier.cover.wizard',
            'ifs.gar.entry.supplier.base.info.wizard',
            'ifs.gar.entry.supplier.contact.wizard',
            'ifs.gar.entry.supplier.account.wizard',
            'ifs.gar.entry.supplier.doc.wizard',
            'ifs.gar.entry.supplier.contract.wizard',
            'ifs.gar.entry.supplier.finish.wizard',
        ]

    t17_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款转让最高额度合同', related='invite_id.t17_contract_info_id')
    t21_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款转让保密协议')
    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书托管协议')
    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='CMCA数字证书订户协议')

    t17_contract_name = fields.Char(
        '应收账款转让最高额度合同', related='t17_contract_info_id.name', readonly=True)
    t17_contract_pdf = fields.Binary(related='t17_contract_info_id.contract')
    t17_contract_state = fields.Selection(related='t17_contract_info_id.state')
    t17_contract_preview = fields.Binary(related='t17_contract_info_id.contract_preview')

    t21_contract_name = fields.Char(
        '应收账款转让保密协议', related='t21_contract_info_id.name', readonly=True)
    t21_contract_pdf = fields.Binary(related='t21_contract_info_id.contract')
    t21_contract_state = fields.Selection(related='t21_contract_info_id.state')
    t21_contract_preview = fields.Binary(related='t21_contract_info_id.contract_preview')

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
            t21_template = self.env['ifs.contract.template'].retrieve_by_code('T21', entry_id.invite_id.factor_id.id)
            f42_template = self.env['ifs.contract.template'].retrieve_by_code(
                'F42', entry_id.invite_id.factor_id.id)
            f43_template = self.env['ifs.contract.template'].retrieve_by_code(
                'F43', entry_id.invite_id.factor_id.id)

            t21_contract = self.env['ifs.contract.info'].create({
                'name': t21_template.name,
                'template_id': t21_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id),
                'partner_two_signature': entry_id.invite_id.factor_id.sudo().signature,
                'partner_two': '%s,%d' % (entry_id.invite_id.factor_id._name, entry_id.invite_id.factor_id.id),
                'params': json.dumps({
                    't17_contract_code': entry_id.invite_id.t17_contract_info_id.code
                })
            })
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
                't21_contract_info_id': t21_contract.id,
                'f42_contract_info_id': f42_contract.id,
                'f43_contract_info_id': f43_contract.id,
            })
        return entry_list

    def write(self, vals):
        res = super().write(vals)
        if 'product_scope' in vals or 'total_quota' in vals or 'email' in vals or 'phone' in vals:
            self.invite_id.t17_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
                'params': json.dumps({
                    'product_scope': self.product_scope,
                    'contract_total_quota': self.total_quota / 10000, # 单位：万元
                    'fee_solution_contract_content': self.fee_solution_id.contract_content,
                }),
            })
            self.t21_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
            self.f43_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
        elif 'bank_id' in vals:
            self.invite_id.t17_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
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

        factor_supplier = self.env['ifs.gar.partner.factor.supplier'].search([
            ('entry_id', '=', self.id)], limit=1)
        factor_supplier.write({
            't17_contract_info_id': self.t17_contract_info_id.id,
            't21_contract_info_id': self.t21_contract_info_id.id,
            'f42_contract_info_id': self.f42_contract_info_id.id,
            'f43_contract_info_id': self.f43_contract_info_id.id,
        })
