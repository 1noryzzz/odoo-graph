# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvTradeOrderWithdrawalConfirmWizard(models.TransientModel):
    _inherit = 'ifs.gar.trade.order.withdrawal.confirm.wizard'

    payment_mode = fields.Selection(
        related='trade_order_id.payment_mode', string='还款方式')
    plan_ids = fields.One2many(
        'ifs.gar.payment.plan', string='还款计划', related='trade_order_id.plan_ids')
