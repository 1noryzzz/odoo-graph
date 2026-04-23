# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
import logging

from odoo import _, api, fields, models
import json
_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecvTradeOrder(models.Model):
    _inherit = 'ifs.gar.trade.order'

    d08_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款结清证明')
    d08_contract_name = fields.Char(
        '应收账款结清证明', related='d08_contract_info_id.name')
    d08_contract_pdf = fields.Binary(
        '应收账款结清证明', related='d08_contract_info_id.contract')
    d08_contract_state = fields.Selection(
        '应收账款结清证明状态', related='d08_contract_info_id.state')
    d08_contract_preview = fields.Binary(
        '应收账款结清证明图片', related='d08_contract_info_id.contract_preview')

    t19_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款转让确认书')
    t19_contract_name = fields.Char(
        '应收账款转让确认书', related='t19_contract_info_id.name')
    t19_contract_pdf = fields.Binary(
        '应收账款转让确认书', related='t19_contract_info_id.contract')
    t19_contract_state = fields.Selection(
        '应收账款转让确认书状态', related='t19_contract_info_id.state')
    t19_contract_preview = fields.Binary(
        '应收账款转让确认书图片', related='t19_contract_info_id.contract_preview')

    d09_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应付账款结清证明')
    d09_contract_name = fields.Char(
        '应付账款结清证明', related='d09_contract_info_id.name')
    d09_contract_pdf = fields.Binary(
        '应付账款结清证明', related='d09_contract_info_id.contract')
    d09_contract_state = fields.Selection(
        '应付账款结清证明状态', related='d09_contract_info_id.state')
    d09_contract_preview = fields.Binary(
        '应付账款结清证明图片', related='d09_contract_info_id.contract_preview')

    t20_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应付账款转让确认书')
    t20_contract_name = fields.Char(
        '应付账款转让确认书', related='t20_contract_info_id.name')
    t20_contract_pdf = fields.Binary(
        '应收账款转让确认书', related='t20_contract_info_id.contract')
    t20_contract_state = fields.Selection(
        '应收账款转让确认书状态', related='t20_contract_info_id.state')
    t20_contract_preview = fields.Binary(
        '应付账款转让确认书图片', related='t20_contract_info_id.contract_preview')

    c13_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款熔断通知书')
    c13_contract_name = fields.Char(
        '应收账款熔断通知书', related='c13_contract_info_id.name')
    c13_contract_pdf = fields.Binary(
        '应收账款熔断通知书', related='c13_contract_info_id.contract')
    c13_contract_state = fields.Selection(
        '应收账款熔断通知书状态', related='c13_contract_info_id.state')
    c13_contract_preview = fields.Binary(
        '应收账款熔断通知书图片', related='c13_contract_info_id.contract_preview')
    
    c14_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='应收账款回转告知函')
    c14_contract_name = fields.Char(
        '应收账款回转告知函', related='c14_contract_info_id.name')
    c14_contract_pdf = fields.Binary(
        '应收账款回转告知函', related='c14_contract_info_id.contract')
    c14_contract_state = fields.Selection(
        '应收账款回转告知函状态', related='c14_contract_info_id.state')
    c14_contract_preview = fields.Binary(
        '应收账款回转告知函图片', related='c14_contract_info_id.contract_preview')

    partner_in_order = fields.Char(
        '当前用户在此单中的角色', compute="_compute_partner_in_order")

    @api.depends('factor_id', 'supplier_id', 'merchant_id')
    def _compute_partner_in_order(self):
        for record in self:
            if record.factor_id.company_id.id == self.env.company.id:
                record.partner_in_order = 'factor'
            elif record.supplier_id.company_id.id == self.env.company.id:
                record.partner_in_order = 'supplier'
            elif record.merchant_id.company_id.id == self.env.company.id:
                record.partner_in_order = 'merchant'
            else:
                record.partner_in_order = ''

    def after_sign(self, next_state):
        if next_state in ('signed', 'committed'):
            return self.confirm_order()

    def pre_confirm_order(self):
        confirm_view = super().pre_confirm_order()

        params = json.dumps({
            't17_contract_code': str(self.sub_loan_account_id.factor_supplier_id.t17_contract_info_id.code),
            'order_code': str(self.order_code),
            'withdrawal_amount': str(self.withdrawal_amount),
            'repayment_date': str(self.repayment_date.strftime('%Y年%m月%d日')),
            'product_scope': self.sub_loan_account_id.factor_supplier_id.product_scope,
            'available_quota': self.sub_loan_account_id.available_quota
        })
        if not self.t19_contract_info_id.id:
            t19_template = self.env['ifs.contract.template'].retrieve_by_code('T19', self.factor_id.id, self.supplier_id.id)
            t19_contract_info = self.env['ifs.contract.info'].create({
                'name': t19_template.name,
                'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                'partner_two': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                'partner_three': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                'template_id': t19_template.id,
                'params': params,
            })
            self.write({
                't19_contract_info_id': t19_contract_info.id
            })
        else:
            self.t19_contract_info_id.write({
                'params': params,
            })

        contract_info_ids = [self.t19_contract_info_id.id]
        sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
            contract_info_ids, self.env.ref('website.default_website').id,
            sign_partner=self.supplier_id, idcard=self.supplier_id.root_employee_id.sudo().identification_id, 
            next_state='signed', token_type='partner_two', ref_object=self)

        confirm_view.get('context').update({
            'default_sign_token_id': sign_token.id,
            'default_sign_url': sign_token.sign_url,
        })

        return confirm_view

    def view_trade_order(self):
        if self.state == 'pending' and self.merchant_id.company_id.id == self.env.company.id:
            params = json.dumps({
                't18_contract_code': str(self.sub_loan_account_id.t18_contract_info_id.code),
                'order_code': str(self.order_code),
                'withdrawal_amount': str(self.withdrawal_amount),
                'repayment_date': str(self.repayment_date.strftime('%Y年%m月%d日')),
                'product_scope': self.sub_loan_account_id.factor_supplier_id.sudo().product_scope,
                'available_quota': self.sub_loan_account_id.available_quota
            })
            if not self.t20_contract_info_id.id:
                t20_template = self.env['ifs.contract.template'].retrieve_by_code('T20', self.factor_id.id, self.supplier_id.id)
                t20_contract_info = self.env['ifs.contract.info'].create({
                    'name': t20_template.name,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'partner_three': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                    'template_id': t20_template.id,
                    'params': params
                })
                self.write({
                    't20_contract_info_id': t20_contract_info.id
                })
            else:
                self.t20_contract_info_id.write({
                    'params': params,
                })

            contract_info_ids = [self.t20_contract_info_id.id]
            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, self.env.ref('website.default_website').id,
                sign_partner=self.merchant_id, idcard=self.merchant_id.root_employee_id.sudo().identification_id,
                next_state='signed', token_type='partner_two', ref_object=self)

            return {
                'name': self.env['ifs.gar.trade.order.withdrawal.confirm.wizard']._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.trade.order.withdrawal.confirm.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_sign_token_id': sign_token.id,
                    'default_sign_url': sign_token.sign_url,
                    'default_trade_order_id': self.id,
                }
            }

        return super().view_trade_order()

    def repaid_order(self):
        super().repaid_order()

        if self.state == 'repaid':
            params = json.dumps({
                'partner_one_name': self.merchant_id.name,
                'partner_two_name': self.factor_id.name,
                't20_contract_date': self.t20_contract_info_id.sign_date.strftime('%Y年%m月%d日'),
                't20_contract_code': self.t20_contract_info_id.code,
                'accounts': self.withdrawal_amount
            })
            if not self.d09_contract_info_id.id:
                d09_template = self.env['ifs.contract.template'].retrieve_by_code('D09', self.factor_id.id)
                d09_contract_info = self.env['ifs.contract.info'].create({
                    'name': d09_template.name,
                    'partner_one': '%s,%d' % (self.merchant_id._name, self.merchant_id.id),
                    'partner_two': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'template_id': d09_template.id,
                    'params': params,
                })

                self.write({
                    'd09_contract_info_id': d09_contract_info.id,
                })
            else:
                self.d09_contract_info_id.write({
                    'params': params,
                })

            self.d09_contract_info_id.signature_all()

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
        
    def action_settle(self):
        super().action_settle()
        
        if self.state == 'settle':
            params = json.dumps({
                't19_contract_date': self.t19_contract_info_id.sign_date.strftime('%Y年%m月%d日'),
                't19_contract_code': self.t19_contract_info_id.code,
                'accounts': self.withdrawal_amount
            })
            if not self.d08_contract_info_id.id:
                d08_template = self.env['ifs.contract.template'].retrieve_by_code('D08', self.factor_id.id)
                d08_contract_info = self.env['ifs.contract.info'].create({
                    'name': d08_template.name,
                    'partner_one': '%s,%d' % (self.factor_id._name, self.factor_id.id),
                    'partner_two': '%s,%d' % (self.supplier_id._name, self.supplier_id.id),
                    'template_id': d08_template.id,
                    'params': params,
                })

                self.write({
                    'd08_contract_info_id': d08_contract_info.id,
                })
            else:
                self.d08_contract_info_id.write({
                    'params': params,
                })

            self.d08_contract_info_id.signature_all()