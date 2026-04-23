# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields


class GuaranteeAccountsRecvOrderBreaker(models.TransientModel):
    _inherit = 'ifs.gar.trade.order.circuit.breaker.wizard'

    c13_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='trade_order_id.c13_contract_info_id', string='应收账款熔断通知书')
    c13_contract_name = fields.Char(
        '应收账款熔断通知书', related='c13_contract_info_id.name')
    c13_contract_pdf = fields.Binary(related='c13_contract_info_id.contract')
    c13_contract_state = fields.Selection(related='c13_contract_info_id.state')
    c13_contract_preview = fields.Binary(
        related='c13_contract_info_id.contract_preview')

    def action_breaker(self):
        if self.trade_order_id.state != 'fuse' and self.trade_order_id.can_fuse:
            contract_info_ids = []

            params = json.dumps({
                't17_contract_code': str(self.trade_order_id.sub_loan_account_id.factor_supplier_id.t17_contract_info_id.code),
                't19_contract_code': str(self.trade_order_id.t19_contract_info_id.code),
                'order_code': str(self.trade_order_id.order_code),
                'withdrawal_amount': str(self.trade_order_id.withdrawal_amount),
            })
            if not self.c13_contract_info_id:
                c13_template = self.env['ifs.contract.template'].retrieve_by_code(
                    'C13', self.factor_id.id, self.supplier_id.id)
                c13_contract_info = self.env['ifs.contract.info'].create({
                    'name': c13_template.name,
                    'partner_one': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                    'partner_two': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'template_id': c13_template.id,
                    'params': params
                })
                self.trade_order_id.write({
                    'c13_contract_info_id': c13_contract_info.id
                })
                contract_info_ids.append(c13_contract_info.id)
            else:
                contract_info_ids.append(self.c13_contract_info_id.id)

            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, website_id=self.env.ref(
                    'website.default_website').id,
                sign_partner=self.supplier_id,
                next_state='signed', ref_object=self)

            return {
                'name': _('请使用手机扫码签约'),
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
        else:
            sup_mer = self.env['ifs.gar.partner.supplier.merchant'].search([('supplier_id','=',self.supplier_id.id),('merchant_id','=',self.merchant_id.id)])
            c14_template = self.env['ifs.contract.template'].search([('code','=','C14')])
            params = json.dumps({
                't18_contract_code': str(sup_mer.t18_contract_info_id.code),
                't19_contract_code': str(self.trade_order_id.t19_contract_info_id.code),
                't20_contract_code': str(self.trade_order_id.t20_contract_info_id.code),
                'order_code': str(self.trade_order_id.order_code),
                'withdrawal_amount': str(self.trade_order_id.withdrawal_amount),
            })
            c14_contract_info = self.env['ifs.contract.info'].create({
                'name': c14_template.name,
                'partner_one': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                'partner_two': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                'template_id': c14_template.id,
                'params': params,
                'partner_two_signature':self.factor_id.signature
            })
            c14_contract_info._contract_sign()
            self.trade_order_id.write({
                'c14_contract_info_id': c14_contract_info.id
            })
            super().action_breaker()

    def after_sign(self, next_state):
        if next_state in ('signed', 'committed'):
            self.trade_order_id.fuse_order()
