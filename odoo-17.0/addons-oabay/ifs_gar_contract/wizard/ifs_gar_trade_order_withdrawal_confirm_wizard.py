# -*- coding: utf-8 -*-
import json

from odoo import _, api, models, fields


class GuaranteeAccountsRecvTradeOrderWithdrawalConfirmWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.withdrawal.confirm.wizard'
    _inherit = [
        'ifs.gar.trade.order.withdrawal.confirm.wizard',
        'ifs.gar.contract.sign.wizard']

    trade_create_date = fields.Datetime(
        '发起日期', related='trade_order_id.create_date')
    seq_code = fields.Char('交易订单编号', related='trade_order_id.seq_code')
