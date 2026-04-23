# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvPaymentPlanWithdraw(models.TransientModel):
    _name = 'ifs.gar.payment.plan.withdraw.wizard'
    _inherit = ['ifs.currency.rmb.mixin']
    _description = '提款确认'

    payment_plan_id = fields.Many2one(
        'ifs.gar.payment.plan', string='还款计划', required=True)

    currency_id = fields.Many2one(
        'res.currency', related='payment_plan_id.currency_id')
    withdraw_state = fields.Selection(
        string='提款状态', related='payment_plan_id.withdraw_state')
    remark = fields.Text('备注')
    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', related='payment_plan_id.factor_id')
    # finance_name = fields.Char('财务联系人姓名', related='factor_id.finance_name')
    # finance_phone = fields.Char('联系电话', related='factor_id.finance_phone')
    account_name = fields.Char('账户名称', related='factor_id.account_name')
    account_no = fields.Char('银行卡号', related='factor_id.account_no')
    deposit_bank = fields.Char('开户行', related='factor_id.deposit_bank')

    withdraw_amount = fields.Monetary(
        '提款金额', related='payment_plan_id.withdraw_amount')
    withdraw_amount_uppercase = fields.Char(
        "提款金额大写", related='payment_plan_id.withdraw_amount_uppercase')
    is_readonly = fields.Boolean('是否只读', compute="_compute_is_readonly")
    
    @api.depends('payment_plan_id.state', 'payment_plan_id.withdraw_state')
    def _compute_is_readonly(self):
        for record in self:
            record.is_readonly = not (
                record.payment_plan_id.trade_order_id.supplier_id.company_id.id == self.env.company.id and record.payment_plan_id.state == 'settle' and record.payment_plan_id.withdraw_state == 'pending')

    def action_withdraw(self):
        self.payment_plan_id.write({
            'remark': self.remark
        })
        self.payment_plan_id.action_withdraw()

    def action_withdraw_confirm(self):
        self.payment_plan_id.write({
            'withdraw_state': 'finished',
        })