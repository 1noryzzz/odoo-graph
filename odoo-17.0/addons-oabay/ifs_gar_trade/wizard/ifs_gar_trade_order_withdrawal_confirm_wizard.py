# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GuaranteeAccountsRecvTradeOrderWithdrawalConfirmWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.withdrawal.confirm.wizard'
    _description = '请款通知书向导'

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', string='交易订单', required=True)
    currency_id = fields.Many2one(
        'res.currency', related='trade_order_id.currency_id')
    state = fields.Selection(
        string='订单状态', related='trade_order_id.state')
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='trade_order_id.merchant_id', required=True)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', related='trade_order_id.supplier_id', required=True)
    order_code = fields.Char(
        string='购销合同编号', related='trade_order_id.order_code', required=True)
    trade_date = fields.Date(
        string='交易时间', related='trade_order_id.trade_date', required=True)
    withdrawal_amount = fields.Monetary(
        string='本次提款金额', related='trade_order_id.withdrawal_amount')
    withdrawal_amount_uppercase = fields.Char(
        string='请款金额大写', related='trade_order_id.withdrawal_amount_uppercase')
    credit_term = fields.Integer(
        string='账期', related='trade_order_id.credit_term')
    repayment_date = fields.Date(
        string='还款日', related='trade_order_id.repayment_date', required=True)
    item_ids = fields.One2many(
        'ifs.gar.trade.order.item', related='trade_order_id.item_ids', string='订单明细')

    order_info_definition_id = fields.Many2one(
        'ifs.gar.trade.definition', related='trade_order_id.order_info_definition_id', string='交易订单配置id')
    order_info = fields.Properties(
        '交易订单相关信息', related='trade_order_id.order_info', definition='order_info_definition_id.params_definition')
    
    can_refuse = fields.Boolean('可拒绝', compute="_compute_can_refuse")
    
    @api.depends('state')
    def _compute_can_refuse(self):
        for record in self:
            record.can_refuse = (record.state == 'pending' and self.merchant_id.company_id.id == self.env.company.id)

    def action_confirm(self):
        return self.trade_order_id.confirm_order()

    def action_refuse(self):
        if self.can_refuse:
            return self.trade_order_id.refuse_order()
