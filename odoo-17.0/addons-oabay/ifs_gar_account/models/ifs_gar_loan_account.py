# -*- coding: utf-8 -*-

import logging

from functools import reduce
from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)


class InclusiveFinancingLoanAccount(models.Model):
    _name = 'ifs.gar.loan.account'
    _description = '鸥贝云贷款账户'
    _inherits = {'ifs.gar.partner.factor.merchant': 'factor_merchant_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin', 'ifs.ir.sequence.mixin']
    _order = 'write_date desc'
    _rec_name = 'seq_code'

    state = fields.Selection([
        ('draft', '未启用'),
        ('normal', '正常'),
        ('overdue', '逾期'),
        ('freeze', '冻结'),
    ], string='账户状态', default='normal', tracking=True)
    active = fields.Boolean('是否启用', default=True, tracking=True)
    factor_merchant_id = fields.Many2one(
        'ifs.gar.partner.factor.merchant', required=True, ondelete='restrict', auto_join=True, index=True,
        string='贷款主体', help='贷款主体')
    currency_id = fields.Many2one(
        'res.currency', related='merchant_id.currency_id')
    legal_name = fields.Char(
        '法人姓名', related='merchant_id.legal_name')
    principal_name = fields.Char(
        string='负责人', related="merchant_id.principal_name")

    sub_account_ids = fields.One2many(
        'ifs.gar.sub.loan.account', 'loan_account_id', string='子账户')

    credit_term = fields.Integer('账期(月)', default=1)
    repay_day = fields.Integer('还款日', default=15)

    approved_quota = fields.Monetary(
        '授信额度', compute='_compute_quota')
    available_quota = fields.Monetary(
        '可用额度', compute='_compute_quota')
    freeze_quota = fields.Monetary(
        '冻结额度', compute='_compute_quota')
    used_quota = fields.Monetary('已用额度', compute='_compute_quota')

    # penalty_interest_rate = fields.Percent(
    #     string='滞纳金利率', required=True, default=5.0, tracking=True)
    # damages_interest_rate = fields.Percent(
    #     string='违约金利率', required=True, default=2.0, tracking=True)
    # is_compound_interest = fields.Boolean(
    #     string='是否复利', required=True, default=True, tracking=True)

    @api.depends('sub_account_ids', 'sub_account_ids.approved_quota', 'sub_account_ids.state')
    def _compute_quota(self):
        for acc in self:
            quota = reduce(lambda prev, curr: {
                'approved_quota': prev.get('approved_quota') + (curr.approved_quota if curr.state == 'normal' else 0.0),
                'freeze_quota': prev.get('freeze_quota') + (curr.freeze_quota if curr.state != 'draft' else 0.0),
                'used_quota': prev.get('used_quota') + (curr.used_quota if curr.state != 'draft' else 0.0),
            }, acc.sub_account_ids, {
                'approved_quota': 0.0,
                'freeze_quota': 0.0,
                'used_quota': 0.0,
            })
            quota['available_quota'] = quota.get('approved_quota') - \
                (quota.get('freeze_quota') + quota.get('used_quota'))
            acc.update(quota)

    # 账户不可删除，只能设置为不可用
    def unlink(self):
        self.write({'active': False})


class InclusiveFinancingSubLoanAccount(models.Model):
    _name = 'ifs.gar.sub.loan.account'
    _description = '鸥贝云贷款账户下，采购方在供应方下的子账户'
    _inherits = {'ifs.gar.partner.supplier.merchant': 'supplier_merchant_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc'
    _rec_name = 'seq_code'

    seq_code = fields.Char('账户编号', required=True, copy=False, readonly=True)
    loan_account_id = fields.Many2one(
        'ifs.gar.loan.account', string='主贷款账户', auto_join=True, index=True, required=True)
    supplier_merchant_id = fields.Many2one(
        'ifs.gar.partner.supplier.merchant', required=True, ondelete='restrict', auto_join=True, index=True,
        string='贷款主体', help='贷款主体')

    state = fields.Selection([
        ('draft', '未启用'),
        ('normal', '正常'),
        ('overdue', '逾期'),
        ('freeze', '冻结'),
    ], string='账户状态', default='normal', tracking=True)
    active = fields.Boolean('是否启用', default=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency', related='loan_account_id.currency_id')

    approved_quota = fields.Monetary('授信额度', required=True, readonly=True)
    available_quota = fields.Monetary(
        '可用额度', compute='_compute_quota', store=True)
    freeze_quota = fields.Monetary(
        '冻结额度', compute='_compute_quota', store=True)
    used_quota = fields.Monetary('已用额度', compute='_compute_quota', store=True)

    credit_term = fields.Integer('账期(月)', related='loan_account_id.credit_term')
    repay_day = fields.Integer('还款日', related='loan_account_id.repay_day')

    bill_ids = fields.One2many(
        'ifs.gar.loan.account.bill', 'sub_loan_account_id', string='账单列表')
    
    reason = fields.Char('注销理由')

    # penalty_interest_rate = fields.Percent(
    #     string='滞纳金利率', required=True, default=5.0, tracking=True)
    # damages_interest_rate = fields.Percent(
    #     string='违约金利率', required=True, default=2.0, tracking=True)
    # is_compound_interest = fields.Boolean(
    #     string='是否复利', required=True, default=True, tracking=True)

    # 基本信息
    merchant_code = fields.Char('采购方编号', related='merchant_id.seq_code')
    merchant_name = fields.Char('采购方名称', related='merchant_id.name')
    supplier_code = fields.Char('供应方编号', related='supplier_id.seq_code')
    supplier_name = fields.Char('供应方名称', related='supplier_id.name')

    @api.depends('approved_quota', 'bill_ids.freeze_quota', 'bill_ids.used_quota')
    def _compute_quota(self):
        for acc in self:
            quota = reduce(lambda prev, curr: {
                'freeze_quota': prev.get('freeze_quota') + (curr.freeze_quota if curr.state == 'current' else 0.0),
                'used_quota': prev.get('used_quota') + (
                    curr.used_quota if curr.state not in ('paid', 'settle') else 0.0),
            }, acc.bill_ids, {
                'freeze_quota': 0.0,
                'used_quota': 0.0,
            })
            quota['available_quota'] = acc.approved_quota - \
                (quota.get('freeze_quota') + quota.get('used_quota'))
            acc.update(quota)

    def _next_sub_code(self, loan_account_id):
        account = self.env['ifs.gar.loan.account'].browse(loan_account_id)
        sub_account_count = self.search_count([
            ('loan_account_id', '=', loan_account_id)
        ])
        return '%s%03d' % (account.seq_code, sub_account_count + 1)

    # 对账户下的账目做日切
    def daliy_cut_off(self):
        self.ensure_one()

        waiting_bills = self.bill_ids.filtered(
            lambda bill: bill.state not in ('paid', 'plan', 'settle'))
        has_overdue = waiting_bills.daliy_cut_off()
        if has_overdue:
            self.write({'state': 'overdue'})
            self.merchant_id.state = 'paused'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['seq_code'] = self._next_sub_code(
                vals.get('loan_account_id')) or _('New')

        return super().create(vals_list)

    # 账户不可删除，只能设置为不可用
    def unlink(self):
        self.write({'active': False})

    def apply_quota(self):
        self.ensure_one()

        return self.env['ifs.gar.upgrade.quota.apply'].start_apply_quota(self)
