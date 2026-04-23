# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields


class GuaranteeAccountsUpgradeQuotaApply(models.Model):
    _inherit = 'ifs.gar.upgrade.quota.apply'

    x10_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='额度调整申请书')
    x10_contract_name = fields.Char(
        '额度调整申请书', related='x10_contract_info_id.name', readonly=True)
    x10_contract_state = fields.Selection(related='x10_contract_info_id.state')
    x10_contract_pdf = fields.Binary(related='x10_contract_info_id.contract')
    x10_contract_preview = fields.Binary(related='x10_contract_info_id.contract_preview')

    x11_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='额度调整确认书')
    x11_contract_name = fields.Char(
        '额度调整申请书', related='x11_contract_info_id.name', readonly=True)
    x11_contract_state = fields.Selection(related='x11_contract_info_id.state')
    x11_contract_pdf = fields.Binary(related='x11_contract_info_id.contract')
    x11_contract_preview = fields.Binary(related='x11_contract_info_id.contract_preview')

    def action_commit(self):
        self.ensure_one()

        if self.merchant_can_confirm:
            params = json.dumps({
                'origin_quota': self.origin_quota,
                'apply_quota': self.apply_quota,
                'apply_reason': self.apply_reason,
                'apply_basis': self.apply_basis,
            })

            if not self.x10_contract_info_id:
                x10_template = self.env['ifs.contract.template'].retrieve_by_code('X10', self.factor_id.id)

                x10_contract = self.env['ifs.contract.info'].create({
                    'name': x10_template.name,
                    'template_id': x10_template.id,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'params': params
                })
                self.x10_contract_info_id = x10_contract
            else:
                self.x10_contract_info_id.update({
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'params': params
                })
            contract_info_ids = [self.x10_contract_info_id.id]
            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, self.env.ref('website.default_website').id,
                sign_partner=self, next_state='signed', token_type='partner_two', ref_object=self)

            return {
                'name': _('额度调整申请书签署'),
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[self.env.ref('ifs_gar_contract.ifs_gar_contract_sign_wizard_view_form').id, 'form']],
                'res_model': 'ifs.gar.contract.sign.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_sign_token_id': sign_token.id,
                    'default_sign_url': sign_token.sign_url,
                }
            }

    def after_sign(self, next_state):
        if next_state in ('signed', 'committed'):
            if self.state == 'draft':
                self.write({
                    'commit_datetime': fields.Datetime.now(),
                    'state': 'committed'
                })
            elif self.state == 'committed':
                self.write({
                    'approval_datetime': fields.Datetime.now(),
                    'state': 'approve'
                })
                self.sub_loan_account_id.approved_quota = self.apply_quota

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
    
    def action_supplier_confirm(self):
        self.ensure_one()
        
        if self.supplier_can_confirm:
            if not self.x11_contract_info_id:
                x11_template = self.env['ifs.contract.template'].retrieve_by_code('X11', self.factor_id.id, self.supplier_id.id)

                self.x11_contract_info_id = self.env['ifs.contract.info'].create({
                    'name': x11_template.name,
                    'template_id': x11_template.id,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'partner_three': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                    'params': json.dumps({
                        'origin_quota': self.origin_quota,
                        'apply_quota': self.apply_quota,
                    })
                })
            else:
                self.x11_contract_info_id.update({
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'partner_three': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                    'params': json.dumps({
                        'origin_quota': self.origin_quota,
                        'apply_quota': self.apply_quota,
                    })
                })
            contract_info_ids = [self.x11_contract_info_id.id]
            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, self.env.ref('website.default_website').id,
                next_state='signed', token_type='partner_three', ref_object=self)

            return {
                'name': _('额度调整申请书签署'),
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[self.env.ref('ifs_gar_contract.ifs_gar_contract_sign_wizard_view_form').id, 'form']],
                'res_model': 'ifs.gar.contract.sign.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_sign_token_id': sign_token.id,
                    'default_sign_url': sign_token.sign_url,
                }
            }
