# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


# class InclusiveFinancingLoanAccountBill(models.Model):
#     _name = 'ifs.gar.loan.account.bill'
#     _inherit = ['ifs.gar.loan.account.bill', 'ifs.currency.rmb.mixin']

#     order_id = fields.Many2one(
#         'ifs.gar.trade.order', compute='_compute_order_id', string='交易编号', store=True)
#     order_ids = fields.One2many(
#         'ifs.gar.trade.order', 'bill_id', string='order')
#     seq_code = fields.Char(string='交易编号', related='order_id.seq_code')
#     order_code = fields.Char(string='基础合同编号', related='order_id.order_code')
#     # accounting_period = fields.Selection(
#     #     string='账期时间',  related='order_id.accounting_period')
#     transaction_amount = fields.Char(
#         compute='_compute_transaction_amount', string='交易金额')
#     loan_date = fields.Datetime(compute='_compute_loan_date', string='动支时间')

#     @api.depends('order_ids')
#     def _compute_order_id(self):
#         for record in self:
#             if record.order_ids:
#                 record.order_id = record.order_ids[0]
#             else:
#                 record.order_id = False

#     @api.depends('bill_log_ids')
#     def _compute_loan_date(self):
#         for record in self:
#             record.loan_date = [
#                 bill_log_id for bill_log_id in record.bill_log_ids if bill_log_id.operate_type == 'loan'][0].create_date

#     @api.depends('loan_amount')
#     def _compute_transaction_amount(self):
#         for record in self:
#             record.transaction_amount = ''.join([
#                 self._format_currency_amount(record.loan_amount),
#                 '（',
#                 self.upper_to_rmb(record.loan_amount),
#                 '）'
#             ])

#     def _format_currency_amount(self, amount):
#         pre = post = u''
#         if self.currency_id.position == 'before':
#             pre = u'{symbol}\N{NO-BREAK SPACE}'.format(
#                 symbol=self.currency_id.symbol or '')
#         else:
#             post = u'\N{NO-BREAK SPACE}{symbol}'.format(
#                 symbol=self.currency_id.symbol or '')
#         return u' {pre}{:,.2f}{post}'.format(amount, pre=pre, post=post)


class InclusiveFinancingLoanAccountBillLog(models.Model):
    _inherit = 'ifs.gar.loan.account.bill.log'

    order_id = fields.Reference(
        selection_add=[
            ('ifs.gar.trade.order', '购销订单'),
            ('ifs.gar.trade.list', '支付订单'),
        ])
