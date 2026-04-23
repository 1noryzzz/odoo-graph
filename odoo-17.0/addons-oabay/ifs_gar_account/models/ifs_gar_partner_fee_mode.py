# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingFeeModeMixin(models.AbstractModel):
    _name = 'ifs.gar.partner.fee.mode.mixin'
    _description = '计费方式模型'

    name = fields.Char('计费方式名称', required=True)
    description = fields.Text('计费方式描述')
    formula = fields.Char('计费公式', compute='_compute_formula')

    def _compute_formula(self):
        for record in self:
            record.formula = f'未实现'

    def calc_fee(self, factor_supplier_id, amount, last_fee):
        self.ensure_one()

        return 0.0


class InclusiveFinancingFeeModeAmount(models.Model):
    _name = 'ifs.gar.partner.fee.mode.amount'
    _inherit = ['ifs.gar.partner.fee.mode.mixin']
    _description = '按总金额的百分比收费'

    rate = fields.Percent(string='费率', default=0.03)

    @api.depends('rate')
    def _compute_formula(self):
        for record in self:
            rate = record.rate * 100
            record.formula = f'金额 * {rate}%'

    def calc_fee(self, factor_supplier_id, amount, last_fee):
        # # 当前项计费
        # current_fee = super().calc_fee(factor_supplier_id, amount, last_fee)

        return amount * self.rate


class InclusiveFinancingFeeModeEach(models.Model):
    _name = 'ifs.gar.partner.fee.mode.each'
    _inherit = ['ifs.gar.partner.fee.mode.mixin']
    _description = '按交易笔数收费'

    currency_id = fields.Many2one(
        'res.currency', string='Account Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    fee = fields.Monetary(string='费用', default=10.0)

    @api.depends('fee')
    def _compute_formula(self):
        for record in self:
            record.formula = f'每笔交易收取{record.fee}元'

    def calc_fee(self, factor_supplier_id, amount, last_fee):
        # # 当前项计费
        # current_fee = super().calc_fee(factor_supplier_id, amount, last_fee)

        return self.fee


class InclusiveFinancingFeeRule(models.Model):
    _inherit = 'ifs.gar.partner.fee.rule'
    _description = '计费规则'

    fee_mode = fields.Reference(selection_add=[
        ('ifs.gar.partner.fee.mode.amount', '按总金额的百分比收费'),
        ('ifs.gar.partner.fee.mode.each', '按交易笔数收费'),
    ], string='计费方式')
    fee_model_name = fields.Char('计费方式数据模型', compute='_compute_fee_mode_info')
    currency_id = fields.Many2one(
        'res.currency', string='Account Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    rate = fields.Percent(
        '费率', compute='_compute_fee_mode_info', readonly=True, inverse='_inverse_fee_mode_info')
    fee = fields.Monetary(
        '费用', compute='_compute_fee_mode_info', readonly=True, inverse='_inverse_fee_mode_info')

    @api.depends('fee_mode')
    def _compute_fee_mode_info(self):
        for record in self:
            record.rate = 0.03
            record.fee = 10.0
            if record.fee_mode and 'rate' in record.fee_mode._fields:
                record.rate = record.fee_mode.rate
            elif record.fee_mode and 'fee' in record.fee_mode._fields:
                record.fee = record.fee_mode.fee
            record.fee_model_name = record.fee_mode._name if record.fee_mode else False

    def _inverse_fee_mode_info(self):
        for record in self:
            if record.fee_mode and 'rate' in record.fee_mode._fields:
                record.fee_mode.rate = record.rate
            elif record.fee_mode and 'fee' in record.fee_mode._fields:
                record.fee_mode.fee = record.fee
