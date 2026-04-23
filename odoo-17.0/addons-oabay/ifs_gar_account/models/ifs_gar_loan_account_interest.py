# -*- coding: utf-8 -*-

import logging

from datetime import datetime, timedelta
from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)


class InclusiveFinancingLoanAccountBillLogInherit(models.Model):
    _inherit = 'ifs.gar.loan.account.bill.log'

    order_id = fields.Reference(
        selection_add=[
            ('ifs.gar.loan.account.interest', '违约金利息'),
            ('ifs.gar.loan.account.interest.log', '日利息'),
            ('ifs.gar.loan.account.damages.log', '违约金')
        ])


class InclusiveFinancingLoanAccountInterest(models.Model):
    _name = 'ifs.gar.loan.account.interest'
    _description = '贷款账户的利息表'
    _inherit = ['ifs.currency.rmb.mixin']
    _order = 'bill_id'

    _sql_constraints = [
        # 一份账单只有一条
        ('loan_account_interest_uniq', 'unique(bill_id, currency_id)',
         '此账单的计息记录已存在')
    ]

    bill_id = fields.Many2one(
        'ifs.gar.loan.account.bill', string='计息账单', required=True, index=True)
    currency_id = fields.Many2one(
        'res.currency', string='币种', related='bill_id.currency_id', store=True)

    # 执行的计息规则（在开始计息时从贷款账户的设置中获得，在整个计息周期里，不随设置的变更而改变）
    penalty_interest_rate = fields.Percent(
        string='滞纳金利率', required=True, readonly=True)
    damages_interest_rate = fields.Percent(
        string='违约金利率', required=True, readonly=True)
    is_compound_interest = fields.Boolean(
        string='是否复利', required=True, default=False, readonly=True)

    interest_amount = fields.Monetary(
        '累计利息', compute='_compute_interest_amount', store=True)
    compound_interest_amount = fields.Monetary(
        '滚动利息（复利）', required=True, default=0.0)

    interest_log_ids = fields.One2many(
        'ifs.gar.loan.account.interest.log', 'interest_id', string='按日计息明细表')

    damages_log_ids = fields.One2many(
        'ifs.gar.loan.account.damages.log', 'interest_id', string='违约金记账明细表')

    @api.depends('damages_log_ids', 'interest_log_ids', 'interest_log_ids.penalty_interest', 'damages_log_ids.damages_interest')
    def _compute_interest_amount(self):
        for interest in self:
            interest_amount = 0.0
            for log in interest.interest_log_ids:
                interest_amount += log.penalty_interest
            for damages in interest.damages_log_ids:
                interest_amount += damages.damages_interest

            interest.interest_amount = interest_amount

    def do_interest(self, account_bill):
        current_time = fields.Datetime.now()

        # 到还款日以后，前3天免息
        start_interest_date_local = fields.Datetime.context_timestamp(
            account_bill, account_bill.repayment_date) + timedelta(days=3)
        interest_date_local = fields.Datetime.context_timestamp(
            account_bill, current_time).replace(hour=0, minute=0, second=0) + timedelta(hours=account_bill.cut_off_time)

        # 计息天数总计 （因为还款日后延了一天，所以这里计息日加一天）
        interest_day_count = (interest_date_local -
                              start_interest_date_local).days + 1
        # 计息明细表里，已存在计息记录的天数
        exist_interest_day_count = 0
        current_interest = self.search([
            ('bill_id', '=', account_bill.id),
            ('currency_id', '=', account_bill.currency_id.id),
        ])
        interest_solution = account_bill.sub_loan_account_id.sudo().factor_supplier_id.interest_solution_id
        if interest_day_count > 0 and not current_interest.exists():
            current_interest = self.create({
                'bill_id': account_bill.id,
                'penalty_interest_rate': interest_solution.penalty_daily_rate if interest_solution else 0.0007,
                'damages_interest_rate': interest_solution.damages_rate if interest_solution else 0.025,
                'is_compound_interest': interest_solution.is_compound_interest if interest_solution else False,
            })
            # self.env['ifs.gar.loan.account.damages.log'].do_damages_interest(
            #             current_interest, start_interest_date_local)
        else:
            exist_interest_day_count = self.env['ifs.gar.loan.account.interest.log'].search_count([
                ('interest_id', '=', current_interest.id)
            ])

        # 这里用来确保，如果日切任务出现中断，造成一段时间未计息，这里可以补上
        if interest_day_count > exist_interest_day_count:
            start_interest_day = start_interest_date_local.day  # 起息日
            for x in range(interest_day_count - exist_interest_day_count, 0, -1):
                # 如果差值是1，意味着只有当天未计息
                c_interest_date_local = interest_date_local - \
                    timedelta(days=(x - 1))

                # day_count = (c_interest_date_local -
                #              start_interest_date_local).days
                # 在后续月份中，对应起息日的天数，变更复利（这里特别计算一次，避免有的月份没有对应天数，比如 31号）
                cdate = datetime(c_interest_date_local.year, c_interest_date_local.month,
                                 1) + timedelta(days=start_interest_day - 1)
                if c_interest_date_local.day == cdate.day: # and day_count > 0:
                    if current_interest.is_compound_interest:
                        current_interest.write({
                            # 用来做复利计算的利息，是当期账单的待还利息，而不是计息里的总计利息，因为总计利息不受还款付息操作影响
                            'compound_interest_amount': (current_interest.bill_id.pending_interest + current_interest.bill_id.pending_damages),
                        })
                    self.env['ifs.gar.loan.account.damages.log'].do_damages_interest(
                        current_interest, c_interest_date_local)    

                self.env['ifs.gar.loan.account.interest.log'].do_day_interest(
                    current_interest, c_interest_date_local)


class InclusiveFinancingLoanAccountInterestLog(models.Model):
    _name = 'ifs.gar.loan.account.interest.log'
    _inherit = ['ifs.currency.rmb.mixin']
    _description = '贷款账户的利息明细'
    _order = 'interest_id, interest_date desc'
    _rec_name = 'interest_date'

    _sql_constraints = [
        # 一份计息表，一天只计一次息
        ('loan_interest_uniq', 'unique(interest_id, interest_date)',
         '今天已计息')
    ]

    interest_id = fields.Many2one(
        'ifs.gar.loan.account.interest', string='计息表', required=True, index=True)
    currency_id = fields.Many2one(
        'res.currency', string='币种', related='interest_id.currency_id', store=True)

    interest_date = fields.Date(string='计息日', required=True, readonly=True)
    principal_amount = fields.Monetary('计息本金', required=True, readonly=True)
    penalty_interest = fields.Monetary('滞纳金', required=True, readonly=True)
    bill_log_id = fields.Many2one(
        'ifs.gar.loan.account.bill.log', string='滞纳金记账记录')

    def do_day_interest(self, interest, interest_date):
        principal_amount = (
            (interest.bill_id.loan_amount - interest.bill_id.repayment_amount) if (interest.bill_id.loan_amount > interest.bill_id.repayment_amount) else 0) + \
            interest.compound_interest_amount

        interest_log = self.env['ifs.gar.loan.account.interest.log'].create({
            'interest_id': interest.id,
            'interest_date': interest_date,
            'principal_amount': principal_amount,
            'penalty_interest': self.up_round(principal_amount * interest.penalty_interest_rate),
        })

        interest_log.bill_log_id = self.env['ifs.gar.loan.account.bill'].insert_bill(
            interest.bill_id.sub_loan_account_id, interest_log, 'interest',
            interest_log.penalty_interest, '[%s]利息' % fields.Date.to_string(
                interest_date),
            record_bill=interest.bill_id)
        
class InclusiveFinancingLoanAccountDamagesLog(models.Model):
    _name = 'ifs.gar.loan.account.damages.log'
    _inherit = ['ifs.currency.rmb.mixin']
    _description = '贷款账户的违约金明细'
    _order = 'interest_id, interest_date desc'
    _rec_name = 'interest_date'

    _sql_constraints = [
        # 一份计息表，一天只计一次息
        ('loan_interest_uniq', 'unique(interest_id, interest_date)',
         '今天已计违约金')
    ]

    interest_id = fields.Many2one(
        'ifs.gar.loan.account.interest', string='计息表', required=True, index=True)
    currency_id = fields.Many2one(
        'res.currency', string='币种', related='interest_id.currency_id', store=True)

    interest_date = fields.Date(string='计算违约金时间', required=True, readonly=True)
    principal_amount = fields.Monetary('计算本金', required=True, readonly=True)
    damages_interest = fields.Monetary('违约金', required=True, readonly=True)
    bill_log_id = fields.Many2one(
        'ifs.gar.loan.account.bill.log', string='违约金记账记录')

    def do_damages_interest(self, interest, interest_date):
        principal_amount = interest.bill_id.pending_amount

        interest_log = self.env['ifs.gar.loan.account.damages.log'].create({
            'interest_id': interest.id,
            'interest_date': interest_date,
            'principal_amount': principal_amount,
            'damages_interest': self.up_round(principal_amount * interest.damages_interest_rate),
        })

        interest_log.bill_log_id = self.env['ifs.gar.loan.account.bill'].insert_bill(
            interest.bill_id.sub_loan_account_id, interest_log, 'damages',
            interest_log.damages_interest, '[%s]违约金' % fields.Date.to_string(
                interest_date),
            record_bill=interest.bill_id)