# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecvTradeOrder(models.Model):
    _inherit = 'ifs.gar.trade.order'

    def _step_models(self):
        step_models = super()._step_models()
        step_models.append('ifs.gar.trade.order.payment.plan.wizard')
        return step_models

    state = fields.Selection(selection_add=[
        ('period_repaid', '分期中'),
        ('fuse', '熔断处理'),
    ], ondelete={'period_repaid': lambda ord: ord.write({'state': 'confirmed'})})
    fuse_remark = fields.Html('熔断原因')

    payment_mode = fields.Selection(selection=[
        ('single', '一次性还款'),
        ('period', '分期还款')
    ], string='还款方式', default='single', help='还款方式')
    period_count = fields.Integer(
        '分期数', default=1, help='分几期')
    fee_payer = fields.Selection(selection=[
        ('merchant', '采购方'),
        ('supplier', '供应方'),
    ], string='手续费支付方', default='supplier', help="下面的还款计划中的手续费由谁支付")
    can_fuse = fields.Boolean(
        '当前用户可否操作熔断', compute='_compute_can_fuse')
    can_accept_fuse = fields.Boolean(
        '当前用户可否确认熔断', compute='_compute_can_accept_fuse')

    plan_ids = fields.One2many(
        'ifs.gar.payment.plan', 'trade_order_id', string='还款计划')
    last_repayment_date = fields.Date(
        '最近还款日', compute='_compute_last_repayment_info')
    last_pending_amount = fields.Monetary(
        '最近待还金额', compute='_compute_last_repayment_info')
    days_left = fields.Integer(
        '剩余天数', compute='_compute_last_repayment_info')
    last_pending_amount_visible = fields.Boolean(
        '最近待还金额是否可见', compute='_compute_last_pending_amount_visible')

    @api.constrains('period_count', 'fee_payer')
    def _check_payment_plan(self):
        for record in self:
            date = datetime.now().date() + relativedelta(months=1)
            if record.withdrawal_amount == 0:
                # 未填写金额，还是填写中的状态，不做校验
                pass
            elif record.payment_mode == 'single':
                if record.fee_payer != 'supplier':
                    raise ValidationError(_('一次性还款，手续费支付方只能是供应方'))

                if record.period_count != 1 or len(record.plan_ids) != 1:
                    raise ValidationError(_('一次性还款，还款计划只能有一条'))
            elif record.payment_mode == 'period':
                if record.period_count != len(record.plan_ids):
                    raise ValidationError(_('分期还款，还款计划数必须等于分期数'))

                repayment_date = record.trade_start_date
                payment_period = 1
                amount = 0.0
                for plan_id in record.plan_ids:
                    if plan_id.payment_period != payment_period:
                        raise ValidationError(_('还款计划中的期数必须连续'))

                    if plan_id.payment_period == record.period_count and plan_id.repayment_date != record.repayment_date:
                        raise ValidationError(_('还款计划最后一期的还款日期必须等于合同最后还款日期'))

                    if plan_id.repayment_date < record.trade_start_date:
                        raise ValidationError(_('还款日期不能小于合同签署日期'))

                    if plan_id.repayment_date < repayment_date:
                        raise ValidationError(_('还款日期不能小于上一期的还款日期'))

                    if plan_id.repayment_date > record.repayment_date:
                        raise ValidationError(_('还款计划中的还款日期不能超过合同最后还款日'))

                    repayment_date = plan_id.repayment_date
                    amount += plan_id.period_amount
                    payment_period += 1

                if amount != record.withdrawal_amount and not (amount > record.withdrawal_amount and amount - record.withdrawal_amount < 1):
                    raise ValidationError(_('还款计划中的还款金额之和必须等于提款金额'))
            if date > record.repayment_date:
                raise ValidationError(_('还款计划中的还款日期必须大于或等于当前时间一个月'))

    @api.depends('plan_ids', 'repayment_date', 'withdrawal_amount')
    def _compute_last_repayment_info(self):
        for record in self:
            plans = record.plan_ids.filtered(
                lambda r: r.state in ['draft', 'waitting', 'overdue']).sorted(key=lambda r: r.repayment_date)
            if plans.exists():
                record.last_repayment_date = plans[0].repayment_date
                record.days_left = plans[0].repayment_date.__sub__(
                    fields.Date.today()).days
                record.last_pending_amount = 0.0
                for plan in plans:
                    if plan.state in ['draft', 'waitting']:
                        record.last_pending_amount += plan.payment_amount
                        break
                    else:
                        record.last_pending_amount += plan.payment_amount
            else:
                record.last_repayment_date = record.repayment_date if record.repayment_date else False
                record.last_pending_amount = record.withdrawal_amount if record.withdrawal_amount else False
                record.days_left = record.repayment_date.__sub__(
                    fields.Date.today()).days if record.repayment_date else False

    @api.depends('state')
    def _compute_last_pending_amount_visible(self):
        for record in self:
            record.last_pending_amount_visible = (
                record.factor_id.company_id.id == self.env.company.id or
                record.merchant_id.company_id.id == self.env.company.id) and record.state in ['pending', 'confirmed', 'period_repaid']

    def _compute_can_fuse(self):
        for record in self:
            record.can_fuse = (
                record.supplier_id.company_id.id == self.env.company.id and record.state in ['confirmed', 'period_repaid'])

    def _compute_can_accept_fuse(self):
        for record in self:
            record.can_accept_fuse = (
                record.factor_id.company_id.id == self.env.company.id and record.state == 'fuse')

    def view_trade_order(self):
        if self.state == 'confirmed':
            # 这里仅用于修复旧数据，旧数据没有还款计划，需要创建
            if not self.plan_ids.exists():
                self.write({
                    'plan_ids': self.env['ifs.gar.payment.plan'].create_plan(self, 1)
                })

        return super().view_trade_order()

    def confirm_order(self):
        res = super().confirm_order()
        if self.state == 'confirmed':
            if self.payment_mode == 'single':
                self.plan_ids.write({
                    'state': 'waitting',
                    'bill_id': self.bill_id.id,
                    'bill_log_id': self.bill_log_id.id
                })
            elif self.payment_mode == 'period':
                period_sum = self.bill_id.pending_amount
                payment_plan_bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    self.sub_loan_account_id, self,
                    'payment_plan', -period_sum, '账单已分期', record_bill=self.bill_id, prev_log=self.bill_log_id)
                for plan in self.plan_ids:
                    bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                        self.sub_loan_account_id, self, 'loan', plan.period_amount,
                        remark=f'账单分期，第({plan.payment_period})期', start_bill_date=self.bill_id.start_bill_date,
                        repayment_date=plan.repayment_date, prev_log=payment_plan_bill_log)
                    # 分期手续费
                    if self.fee_payer == 'merchant':
                        self.env['ifs.gar.loan.account.bill'].insert_bill(
                            self.sub_loan_account_id, self,
                            'fee', plan.fee, f'第({plan.payment_period})期分期手续费', record_bill=bill_log.bill_id, prev_log=bill_log)

                    plan.write({
                        'state': 'waitting',
                        'bill_id': bill_log.bill_id.id,
                        'bill_log_id': bill_log.id
                    })
        return res

    def repaid_order(self):
        self.ensure_one()

        if self.state in ['confirmed', 'period_repaid'] and self.factor_id.company_id.id == self.env.company.id:
            unsettle_plan_ids = self.plan_ids.filtered(
                lambda r: r.state != 'settle')
            if not unsettle_plan_ids.exists():
                self.write({
                    'state': 'repaid',
                })
            else:
                self.write({
                    'state': 'period_repaid'
                })

    def fuse_order(self):
        self.ensure_one()

        if self.can_fuse:
            self.write({
                'state': 'fuse',
            })

    def accept_fuse(self):
        self.ensure_one()

        if self.can_accept_fuse:
            # 往所有的账单里，写入熔断数据，冲平相关的所有账单
            self.plan_ids.do_fuse()
            self.write({
                'state': 'settle'
            })

    def action_settle(self):
        self.ensure_one()

        if self.state == 'repaid':
            self.write({
                'state': 'settle'
            })

    def circuit_breaker(self):
        if self.can_fuse or self.can_accept_fuse:
            return {
                'name': _('应收账款熔断确认'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.trade.order.circuit.breaker.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_trade_order_id': self.id,
                },
            }
