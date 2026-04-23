# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvPaymentPlanReceipt(models.TransientModel):
    _name = 'ifs.gar.payment.plan.receipt.wizard'
    _inherit = ['ifs.currency.rmb.mixin']
    _description = '提交还款凭据'

    payment_plan_id = fields.Many2one(
        'ifs.gar.payment.plan', string='还款计划', required=True)
    payment_receipt = fields.Image('还款凭据', required=True)

    currency_id = fields.Many2one(
        'res.currency', related='payment_plan_id.currency_id')
    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', related='payment_plan_id.factor_id')
    finance_name = fields.Char('财务联系人姓名', related='factor_id.finance_name')
    finance_phone = fields.Char('联系电话', related='factor_id.finance_phone')
    account_name = fields.Char('账户名称', related='factor_id.account_name')
    account_no = fields.Char('银行卡号', related='factor_id.account_no')
    deposit_bank = fields.Char('开户行', related='factor_id.deposit_bank')

    payment_amount = fields.Monetary('还款金额', compute="_compute_payment_amount")
    payment_amount_uppercase = fields.Char(
        "还款金额大写", compute="_compute_payment_amount")

    @api.depends('payment_plan_id')
    def _compute_payment_amount(self):
        for record in self:
            payment_amount = (
                record.payment_plan_id.pending_amount +
                record.payment_plan_id.pending_interest + record.payment_plan_id.pending_fee)
            record.update({
                'payment_amount': payment_amount,
                'payment_amount_uppercase': self.upper_to_rmb(payment_amount)
            })

    def action_confirm(self):
        self.payment_plan_id.write({
            'state': 'repaid',
            'payment_receipt': self.payment_receipt
        })
