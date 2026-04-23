# -*- coding: utf-8 -*-

from odoo import fields, models


class InclusiveFinancingFactoringRecord(models.Model):
    _name = 'ifs.gar.factoring.record'
    _description = '保理放款记录'
    _order = 'id desc'

    collection_order_id = fields.Many2one(
        'ifs.gar.collection.order',
        string='催收单据',
        required=True,
        ondelete='cascade',
        index=True,
    )
    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方',
        required=True,
        ondelete='restrict',
    )
    supplier_id = fields.Many2one(
        'ifs.partner.supplier',
        string='供应方',
        required=True,
        ondelete='restrict',
    )
    payment_time = fields.Char('付款日期', required=True)
    actual_payment_amount = fields.Monetary('实付金额', required=True)
    payment_voucher = fields.Char('付款凭证')
    currency_id = fields.Many2one(
        'res.currency',
        string='币种',
        related='collection_order_id.currency_id',
        store=True,
        readonly=True,
    )

    payer_company = fields.Char('付款公司', related='factor_id.name', readonly=True)
    payer_account = fields.Char('付款账号', related='factor_id.ifs_company_id.account_no', readonly=True)
    payer_bank = fields.Char('付款银行', related='factor_id.ifs_company_id.deposit_bank', readonly=True)
    payee_company = fields.Char('收款公司', related='supplier_id.name', readonly=True)
    payee_account = fields.Char('收款账号', related='supplier_id.ifs_company_id.account_no', readonly=True)
    payee_bank = fields.Char('收款银行', related='supplier_id.ifs_company_id.deposit_bank', readonly=True)
