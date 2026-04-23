# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
import json
from datetime import datetime


class InclusiveFinancingWithdrawalOrder(models.Model):
    _inherit = 'ifs.gar.withdrawal.order'

    d09_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应付账款结清证明')
    d09_contract_name = fields.Char(
        '应付账款结清证明', related='d09_contract_info_id.name')
    d09_contract_pdf = fields.Binary(
        '应付账款结清证明', related='d09_contract_info_id.contract')
    d09_contract_state = fields.Selection(
        '应付账款结清证明状态', related='d09_contract_info_id.state')

    def action_confirm_repay(self):
        if self.state == 'sent':
            contract_info_ids = [self.d09_contract_info_id.id]
            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, self.env.ref('website.default_website').id,
                next_state='signed', token_type='partner_two')
            sign_token.contract_info_ids.with_context(
                uid=sign_token.user_id.id).signature_all()
            self.state = 'approved'

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

    def view_withdrawal_order(self):
        if self.state == 'sent' and self.factor_id.name == self.env.company.name:
            if not self.d09_contract_info_id:
                d09_template = self.env['ifs.contract.template'].retrieve_by_code('D09', self.factor_id.id)
                self.d09_contract_info_id = self.env['ifs.contract.info'].create({
                    'name': d09_template.name,
                    'partner_one': '%s,%d' % ('ifs.partner.merchant', self.merchant_id.id),
                    'partner_two': '%s,%d' % ('ifs.partner.factor', self.factor_id.id),
                    'template_id': d09_template.id,
                    'params': json.dumps({
                        'partner_one_name': self.merchant_id.name,
                        'partner_two_name': self.factor_id.name,
                        't20_contract_date': self.t20_contract_info_id.sign_date.strftime('%Y年%m月%d日'),
                        't20_contract_code': self.t20_contract_info_id.code,
                        'accounts': self.withdrawal_amount
                    }),
                })
        return super().view_withdrawal_order()
