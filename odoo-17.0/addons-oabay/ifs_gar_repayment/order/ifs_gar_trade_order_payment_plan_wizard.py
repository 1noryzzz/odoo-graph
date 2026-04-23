# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, models, fields, Command
from odoo.exceptions import ValidationError


class GuaranteeAccountsRecvTradeOrderPaymentPlanWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.payment.plan.wizard'
    _inherit = ['ifs.gar.order.step', 'ifs.currency.rmb.mixin']
    _description = '还款计划制定向导'

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', string='交易订单', required=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='trade_order_id.merchant_id')
    currency_id = fields.Many2one(
        'res.currency', related='trade_order_id.currency_id')

    merchant_code = fields.Char('采购方编号', related="merchant_id.seq_code")
    merchant_name = fields.Char('采购方名称', related="merchant_id.name")
    merchant_approved_quota = fields.Monetary(
        "授信额度", compute='_compute_quota_info')  # 此处直接用关联字段存在问题，没有过滤掉当前采购方在其他方的相关额度信息，所以使用计算字段，同时其他额度信息也会变正常
    merchant_available_quota = fields.Monetary(
        "可用额度", related='merchant_id.available_quota')
    merchant_used_quota = fields.Monetary(
        "已用额度", related='merchant_id.used_quota')

    order_code = fields.Char(
        string='基础合同编号', related="trade_order_id.order_code")
    trade_amount = fields.Monetary(
        '基础合同金额', related='trade_order_id.trade_amount')
    withdrawal_amount = fields.Monetary(
        "本次提款金额", related='trade_order_id.withdrawal_amount')
    trade_date = fields.Date('合同签署日期', related='trade_order_id.trade_date')
    trade_start_date = fields.Date('账期起始日', related='trade_order_id.trade_start_date')

    credit_term = fields.Integer(
        "账期设定（天）", related='trade_order_id.credit_term', help='账期，单位为月')
    repayment_date = fields.Date(
        string='还款日', related="trade_order_id.repayment_date")
    days_left = fields.Integer("剩余天数", related="trade_order_id.days_left")

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
    plan_ids = fields.One2many(
        'ifs.gar.payment.plan', string='还款计划', compute='_compute_plan_ids')

    def _compute_plan_ids(self):
        for wizard in self:
            wizard.plan_ids = wizard.trade_order_id.plan_ids

    @api.depends('merchant_id')
    def _compute_quota_info(self):
        for record in self:
            if record.merchant_id:
                record.merchant_approved_quota = record.merchant_id.approved_quota
            else:
                record.merchant_approved_quota = False

    @api.onchange('payment_mode')
    def _onchange_payment_mode(self):
        if self.payment_mode == 'period':
            self.update({
                'period_count': 3,
                'fee_payer': 'merchant'
            })

    @api.onchange('payment_mode', 'period_count')
    def _onchange_payment_period(self):
        if self.payment_mode == 'single':
            self.period_count = 1

        if self.period_count == 1:
            self.fee_payer = 'supplier'

        self.plan_ids = self.env['ifs.gar.payment.plan'].create_plan(
            self.trade_order_id, self.period_count)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if 'plan_ids' in vals:
            res.trade_order_id.write({
                'plan_ids': vals.get('plan_ids')
            })
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'plan_ids' in vals:
            self.trade_order_id.write({
                'plan_ids': vals.get('plan_ids')
            })
        return res

    def action_next(self):
        self.trade_order_id.write({
            'payment_mode': self.payment_mode,
            'period_count': self.period_count,
            'fee_payer': self.fee_payer,
        })

        if self.has_next_step:
            return super().action_next()
        else:
            return self.trade_order_id.pre_confirm_order()

    def action_approved_quota(self):
        self.ensure_one()
        sub_loan_account_id = self.env['ifs.gar.sub.loan.account'].search(
            [('supplier_id', '=', self.trade_order_id.supplier_id.id), ('merchant_id', '=', self.merchant_id.id)])
        if sub_loan_account_id:
            return {
                'name': _('子账户列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.sub.loan.account',
                'res_id': False,
                'domain': [('id', '=', sub_loan_account_id.id)],
                'target': 'new',
            }

    def action_available_quota(self):
        self.ensure_one()
        if self.merchant_id:
            return {
                'name': _('订单列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.trade.order',
                'res_id': False,
                'domain': [('merchant_id', '=', self.merchant_id.id)],
                'target': 'new',
            }

    def action_used_quota(self):
        pass
