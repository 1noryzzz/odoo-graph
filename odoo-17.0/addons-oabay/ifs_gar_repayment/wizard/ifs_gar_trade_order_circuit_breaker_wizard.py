# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvOrderBreaker(models.TransientModel):
    _name = 'ifs.gar.trade.order.circuit.breaker.wizard'
    _inherit = ['ifs.currency.rmb.mixin']
    _description = '熔断应收账款订单的确认'

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', required=True,
        ondelete='restrict', string='交易订单信息', help='对应的交易订单')

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', related='trade_order_id.factor_id')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', related='trade_order_id.supplier_id')
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='trade_order_id.merchant_id')

    currency_id = fields.Many2one(
        'res.currency', related='trade_order_id.currency_id')
    trade_state = fields.Selection(
        string='还款状态', related='trade_order_id.state')
    order_code = fields.Char(
        string='基础合同编号', related='trade_order_id.order_code')
    trade_amount = fields.Monetary(
        '基础合同金额', related='trade_order_id.trade_amount')
    withdrawal_amount = fields.Monetary(
        "本次提款金额", related='trade_order_id.withdrawal_amount')
    trade_date = fields.Date(
        '合同签署日期', related='trade_order_id.trade_date')
    trade_start_date = fields.Date(
        '账期起始日', related='trade_order_id.trade_start_date')
    credit_term = fields.Integer(
        "账期设定(天)", help='账期，单位为天', related='trade_order_id.credit_term')
    repayment_date = fields.Date(
        string='还款日', related='trade_order_id.repayment_date')
    days_left = fields.Integer("剩余天数", related='trade_order_id.days_left')

    order_bills_amount = fields.Monetary(
        '当前应收账款余额', compute='_compute_order_bills_info')
    order_bills_amount_uppercase = fields.Char(
        '当前应收账款余额大写', compute='_compute_order_bills_info')
    fee_amount = fields.Monetary(
        '需支付手续费', compute='_compute_order_bills_info')
    fuse_remark = fields.Html('熔断原因', related='trade_order_id.fuse_remark', readonly=False)

    @api.depends('trade_order_id')
    def _compute_order_bills_info(self):
        for record in self:
            pending_plan_ids = record.trade_order_id.plan_ids.filtered(
                lambda r: r.state in ['waitting', 'repaid', 'overdue'])
            if len(pending_plan_ids.ids) > 0:
                record.order_bills_amount = sum(
                    pending_plan_ids.mapped('pending_amount'))
                record.order_bills_amount_uppercase = self.upper_to_rmb(
                    record.order_bills_amount)
                record.fee_amount = sum(pending_plan_ids.mapped(
                    'pending_fee')) + sum(pending_plan_ids.mapped('pending_inner_fee'))
            else:
                record.order_bills_amount = 0
                record.order_bills_amount_uppercase = ''
                record.fee_amount = 0

    def action_breaker(self):
        if self.trade_order_id.state != 'fuse' and self.trade_order_id.can_fuse:
            self.trade_order_id.fuse_order()
        elif self.trade_order_id.can_accept_fuse:
            self.trade_order_id.accept_fuse()
