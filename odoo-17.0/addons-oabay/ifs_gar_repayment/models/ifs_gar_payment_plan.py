# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
from odoo import _, api, models, fields, Command
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class InclusiveFinancingPaymentPlan(models.Model):
    _name = 'ifs.gar.payment.plan'
    _description = '还款计划'
    _inherit = ['ifs.ir.sequence.mixin', 'ifs.currency.rmb.mixin']
    _order = "trade_order_id desc, payment_period"

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', required=True,
        ondelete='restrict', index=True, string='交易订单信息', help='当前提款单对应的交易订单')
    currency_id = fields.Many2one(
        'res.currency', related='trade_order_id.currency_id')
    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', related='trade_order_id.factor_id')
    account_name = fields.Char('账户名称', related='factor_id.account_name')
    account_no = fields.Char('银行卡号', related='factor_id.account_no')
    deposit_bank = fields.Char('开户行', related='factor_id.deposit_bank')
    trade_state = fields.Selection(
        string='还款状态', related='trade_order_id.state')

    payment_period = fields.Integer(
        '还款期数', required=True, help='当前还款计划对应的还款期数')
    state = fields.Selection(string='还款状态', selection=[
        ('draft', '草稿'),
        ('waitting', '待还款'),
        ('repaid', '已还款'),
        ('settle', '已确认'),
        ('overdue', '已逾期'),
    ], readonly=True, default='draft')
    withdraw_state = fields.Selection(string='提款状态', selection=[
        ('pending', '未打款'),
        ('waiting', '待打款'),
        ('finished', '已打款'),
    ], readonly=True, default='pending')

    repayment_date = fields.Date(
        string='还款日', required=True)
    days_left = fields.Integer("剩余天数", compute="_compute_days_left")
    period_amount = fields.Monetary('当期本金', default=0.0)
    fee = fields.Monetary('预估手续费', compute="_compute_fee", store=True)

    can_repayment = fields.Boolean('可还款', compute="_compute_can_repayment")
    can_confirm = fields.Boolean('可确认', compute="_compute_can_confirm")
    payment_receipt = fields.Image(string='还款凭证')

    bill_id = fields.Many2one(
        'ifs.gar.loan.account.bill', string='记账账单', ondelete='restrict')
    bill_log_id = fields.Many2one(
        'ifs.gar.loan.account.bill.log', string='生效的关联日志')

    loan_amount = fields.Monetary(
        '本期贷款金额', related='bill_id.loan_amount')
    repayment_amount = fields.Monetary(
        '已还款金额', related='bill_id.repayment_amount')
    pending_amount = fields.Monetary(
        '待还本金', compute='_compute_pending_amount')
    pending_interest = fields.Monetary(
        '待还利息', compute='_compute_pending_amount')
    pending_fee = fields.Monetary(
        '待还手续费', compute='_compute_pending_amount')
    pending_inner_fee = fields.Monetary(
        '待扣手续费', compute='_compute_payment_amount')
    pending_fee_visible = fields.Boolean(
        '待还手续费是否可见', compute="_compute_pending_fee_visible")
    pending_inner_fee_visible = fields.Boolean(
        '待扣手续费是否可见', compute="_compute_pending_inner_fee_visible")

    payment_amount = fields.Monetary('还款金额', compute="_compute_payment_amount")
    payment_amount_uppercase = fields.Char(
        "还款金额大写", compute="_compute_payment_amount")
    withdraw_amount = fields.Monetary(
        '提款金额', compute="_compute_payment_amount")
    withdraw_amount_uppercase = fields.Char(
        "提款金额大写", compute="_compute_payment_amount")

    remark = fields.Text('备注')
    can_withdraw = fields.Boolean('可提款', compute="_compute_can_withdraw")
    can_payment = fields.Boolean('可打款', compute="_compute_can_payment")

    @api.depends('repayment_date')
    def _compute_days_left(self):
        for record in self:
            record.days_left = (
                record.repayment_date - fields.Date.today()).days

    @api.depends('period_amount')
    def _compute_fee(self):
        for record in self:
            record.fee = self.up_round(record.period_amount * 0.03)

    @api.depends('state')
    def _compute_can_repayment(self):
        for record in self:
            record.can_repayment = (
                record.trade_order_id.merchant_id.company_id.id == self.env.company.id and
                record.state in ['waitting', 'overdue'] and
                record.id == self.search([
                    ('trade_order_id', '=', record.trade_order_id.id),
                    ('state', 'in', ['waitting', 'repaid', 'overdue'])], limit=1).id)

    @api.depends('state')
    def _compute_can_confirm(self):
        for record in self:
            record.can_confirm = (
                record.trade_order_id.factor_id.company_id.id == self.env.company.id and
                record.state == 'repaid')

    @api.depends('state', 'bill_id')
    def _compute_pending_amount(self):
        for record in self:
            record.pending_amount = 0.0
            record.pending_interest = 0.0
            record.pending_fee = 0.0
            if record.bill_id and record.state != 'settle':
                record.pending_amount = record.bill_id.pending_amount
                record.pending_interest = record.bill_id.pending_interest
                record.pending_fee = record.bill_id.fee

    @api.depends('trade_order_id.fee_payer')
    def _compute_pending_fee_visible(self):
        for record in self:
            record.pending_fee_visible = (
                record.trade_order_id.factor_id.company_id.id == self.env.company.id or
                record.trade_order_id.supplier_id.company_id.id == self.env.company.id or
                record.trade_order_id.merchant_id.company_id.id == self.env.company.id) and record.trade_order_id.fee_payer == 'merchant'

    @api.depends('trade_order_id.fee_payer')
    def _compute_pending_inner_fee_visible(self):
        for record in self:
            record.pending_inner_fee_visible = (
                record.trade_order_id.factor_id.company_id.id == self.env.company.id or
                record.trade_order_id.supplier_id.company_id.id == self.env.company.id) and record.trade_order_id.fee_payer == 'supplier'

    @api.depends('state', 'withdraw_state')
    def _compute_can_withdraw(self):
        for record in self:
            record.can_withdraw = (
                record.trade_order_id.supplier_id.company_id.id == self.env.company.id and record.state == 'settle' and record.withdraw_state == 'pending')

    @api.depends('state', 'withdraw_state')
    def _compute_can_payment(self):
        for record in self:
            record.can_payment = (
                record.factor_id.company_id.id == self.env.company.id and record.state == 'settle' and record.withdraw_state == 'waiting')

    @api.depends('bill_id', 'bill_id.pending_amount', 'bill_id.pending_interest', 'bill_id.fee', 'bill_id.bill_amount')
    def _compute_payment_amount(self):
        for record in self:
            if not record.bill_id.fee and record.trade_order_id.fee_payer == 'supplier':
                record.pending_inner_fee = record.fee
            else:
                record.pending_inner_fee = False
            if record.state != 'settle':
                payment_amount = (
                    record.pending_amount +
                    record.pending_interest + record.pending_fee)
                withdraw_amount = (
                    record.pending_amount -
                    record.pending_inner_fee)
            else:
                payment_amount = (
                    record.bill_id.bill_amount +
                    record.pending_interest)
                withdraw_amount = (
                    record.bill_id.bill_amount -
                    record.bill_id.fee - record.pending_inner_fee)
            record.update({
                'payment_amount': payment_amount,
                'payment_amount_uppercase': self.upper_to_rmb(payment_amount),
                'withdraw_amount': withdraw_amount,
                'withdraw_amount_uppercase': self.upper_to_rmb(withdraw_amount)
            })

    @api.model
    def create_plan(self, trade_order, period_count):
        '''
        创建还款计划
        '''
        payment_period = 1
        start_bill_date = trade_order.trade_start_date
        repayment_date = trade_order.repayment_date - \
            relativedelta(months=(period_count - payment_period))
        if repayment_date <= start_bill_date:
            repayment_date = start_bill_date + relativedelta(days=1)

        plan_ids = [Command.clear()]
        while payment_period <= period_count:
            period_amount = self.up_round(
                trade_order.withdrawal_amount / period_count)
            if payment_period == period_count:
                repayment_date = trade_order.repayment_date

            plan_ids += [
                Command.create({
                    'trade_order_id': trade_order.id,
                    'state': 'waitting' if trade_order.state == 'confirmed' else 'draft',
                    'payment_period': payment_period,
                    'repayment_date': repayment_date,
                    'period_amount': period_amount,
                    'bill_id': trade_order.bill_id.id if trade_order.state == 'confirmed' and period_count == 1 else False,
                    'bill_log_id': trade_order.bill_log_id.id if trade_order.state == 'confirmed' and period_count == 1 else False,
                })
            ]

            repayment_date = repayment_date + relativedelta(months=1)
            if repayment_date > trade_order.repayment_date:
                repayment_date = trade_order.repayment_date
            payment_period += 1

        return plan_ids

    def action_repay(self):
        if self.can_repayment:
            return {
                'name': _('提交还款凭据'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.payment.plan.receipt.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_payment_plan_id': self.id,
                },
            }

    def action_confirm(self):
        if self.can_confirm:
            return {
                'name': _('确认收款'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[self.env.ref('ifs_gar_repayment.ifs_gar_payment_plan_view_form_confirm').id, 'form']],
                'res_model': 'ifs.gar.payment.plan',
                'res_id': self.id,
                'target': 'new',
                'context': {
                    'default_payment_plan_id': self.id,
                },
            }

    def action_settle(self):
        self.ensure_one()
        if self.can_confirm:
            if not self.bill_id.is_bill_paided():
                bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    self.trade_order_id.sub_loan_account_id, self.trade_order_id, 'repayment', -
                    self.payment_amount,
                    remark='交易结算，还款', repayment_date=self.repayment_date, record_bill=self.bill_id, prev_log=self.bill_log_id)
            else:
                _logger.error(f'还款计划[{self.id}]在确认时，账单被标记为已还款状态，需核实数据！')

            if self.bill_id.is_bill_paided():
                self.write({
                    'bill_log_id': bill_log.id,
                })
            else:
                _logger.error(f'还款计划[{self.id}]在确认时，还款后账单未还清，需核实数据！')
                raise ValidationError(_('还款失败，账单信息不一致，请联系管理员！'))
            self.write({
                'state': 'settle',
            })
            self.trade_order_id.repaid_order()

    def do_fuse(self):
        for plan in self:
            if not plan.bill_id.is_bill_paided():
                bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    plan.trade_order_id.sub_loan_account_id, plan.trade_order_id, 'fuse', -plan.payment_amount,
                    remark='交易结算，熔断', repayment_date=plan.repayment_date, record_bill=plan.bill_id, prev_log=plan.bill_log_id)
            else:
                _logger.error(f'还款计划[{plan.id}]在熔断时，账单被标记为已还款状态，需核实数据！')

            if plan.bill_id.is_bill_paided():
                plan.write({
                    'bill_log_id': bill_log.id,
                    'state': 'settle',
                    'withdraw_state': 'finished',
                })
            else:
                _logger.error(f'还款计划[{plan.id}]在熔断时，还款后账单未还清，需核实数据！')
                raise ValidationError(_('熔断失败，账单信息不一致，请联系管理员！'))

    def start_withdraw(self):
        if self.can_withdraw:
            return {
                'name': _('发起提款'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.payment.plan.withdraw.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_payment_plan_id': self.id,
                },
            }

    def action_withdraw(self):
        self.ensure_one()
        if self.can_withdraw:
            self.write({
                'withdraw_state': 'waiting',
            })
            unsettle_plan_ids = self.trade_order_id.plan_ids.filtered(
                lambda r: r.state != 'settle')
            if not unsettle_plan_ids.exists():
                self.trade_order_id.action_settle()

    def action_withdraw_confirm(self):
        if self.can_payment:
            return {
                'name': _('发起打款'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.payment.plan.withdraw.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_payment_plan_id': self.id,
                    'default_remark': self.remark,
                },
            }
