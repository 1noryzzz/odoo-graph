# -*- coding: utf-8 -*-

import logging

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from functools import reduce
from typing import TYPE_CHECKING, cast

import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.galaxy_common.fields import local_to_utc

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from odoo.addons.ifs_gar_post_loan_manage.models.ifs_gar_collection_order import InclusiveFinancingCollectionOrder


class InclusiveFinancingLoanAccountBill(models.Model):
    _name = 'ifs.gar.loan.account.bill'
    _description = '保理账户的周期账单表'
    _order = 'code desc'
    _rec_name = 'code'

    _sql_constraints = [
        # 同一个账户，允许有多币种的账单存在，比如美元账单和人民币账单
        ('loan_account_code_uniq', 'unique(sub_loan_account_id, code, currency_id)',
         '账户的当期账单已存在')
    ]

    code = fields.Char(
        '账单编号', required=True, readonly=True)  # 4位年 + 2位月份 + 顺序号
    loan_account_id = fields.Many2one(
        'ifs.gar.loan.account', string='贷款主账户', related='sub_loan_account_id.loan_account_id')
    sub_loan_account_id = fields.Many2one(
        'ifs.gar.sub.loan.account', ondelete='restrict', string='贷款子账户', required=True)
    factor_id = fields.Many2one(
        'ifs.partner.factor',
        string='保理方', related='loan_account_id.factor_merchant_id.factor_id')
    merchant_id = fields.Many2one(
        'ifs.partner.merchant',
        string='采购方', related='loan_account_id.factor_merchant_id.merchant_id')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier',
        string='供应方', related='sub_loan_account_id.supplier_id')
    legal_name = fields.Char(
        '法人姓名', related='loan_account_id.legal_name')
    principal_name = fields.Char(
        string='负责人', related="loan_account_id.principal_name")

    state = fields.Selection([
        ('current', '未出账单'),
        ('pending', '待还账单'),
        ('overdue', '逾期'),
        ('paid', '已还账单'),
        ('plan', '已分期'),
        ('settle', '结清账单')
    ], string='账单状态', default='current')

    start_bill_date = fields.Datetime(
        string='账单开始时间', readonly=True)
    # 这几个字段，在创建账单时写入，不可修改
    cut_off_time = fields.Float('日切时间', required=True, readonly=True)
    bill_date = fields.Datetime(string='账单日', required=True, readonly=True)
    repayment_date = fields.Datetime(
        string='还款日', required=True, readonly=True)
    currency_id = fields.Many2one(
        'res.currency', string='币种', required=True)

    freeze_quota = fields.Monetary(
        '冻结额度', compute='_compute_quota', store=True)
    used_quota = fields.Monetary('已用额度', compute='_compute_quota', store=True)
    loan_amount = fields.Monetary(
        '贷款金额', compute='_compute_quota', store=True)
    repayment_amount = fields.Monetary(
        '已还款金额', compute='_compute_quota', store=True)
    pending_amount = fields.Monetary(
        '待还金额', compute='_compute_quota', store=True)
    pending_interest = fields.Monetary(
        '滞纳金', compute='_compute_quota', store=True)
    pending_damages = fields.Monetary(
        '违约金', compute='_compute_quota', store=True)
    fee = fields.Monetary(
        '手续费', compute='_compute_quota', store=True)

    bill_amount = fields.Monetary('账单金额', default=0.0)

    bill_log_ids = fields.One2many(
        'ifs.gar.loan.account.bill.log', 'bill_id', string='动账记录')

    approved_quota = fields.Monetary(
        '批复额度', readonly=True, related='sub_loan_account_id.approved_quota')

    # interest_ids = fields.One2many(
    #     'factoring.loan.account.interest', 'bill_id', string='计息信息')
    # interest_id = fields.Many2one(
    #     'factoring.loan.account.interest', string='计息信息', compute='_compute_interest_info', store=True)
    # is_overdue = fields.Boolean(
    #     '是否逾期', compute='_compute_interest_info', store=True)
    # overdue_days = fields.Integer(
    #     string='逾期天数', compute='_compute_interest_info')
    # overdue_interest = fields.Monetary(
    #     string='逾期利息', related='interest_id.interest_amount')

    @api.depends('bill_log_ids.operate_type', 'bill_log_ids.amount')
    def _compute_quota(self):
        for bill in self:
            bill.update(
                reduce(lambda prev, curr: {
                    'freeze_quota': prev.get('freeze_quota') + (
                        curr.amount if curr.operate_type in ('freeze', 'unfreeze') else 0.0),
                    'used_quota': prev.get('used_quota') + (
                        curr.amount if curr.operate_type in ('loan', 'refund', 'repayment', 'payment_plan', 'fuse', 'damages', 'interest', 'pay_interest') else 0.0),
                    'loan_amount': prev.get('loan_amount') + (
                        curr.amount if curr.operate_type in ('loan', 'refund', 'payment_plan') else 0.0),
                    'repayment_amount': prev.get('repayment_amount') + (
                        -curr.amount if curr.operate_type in ('repayment', 'pay_interest', 'fuse') else 0.0),
                    'pending_amount': prev.get('pending_amount') + (
                        curr.amount if bill.state not in ('paid', 'settle') and curr.operate_type in ('loan', 'refund', 'repayment', 'payment_plan', 'fuse', 'damages', 'interest', 'pay_interest') else 0.0),
                    'pending_interest': prev.get('pending_interest') + (
                        curr.amount if bill.state not in ('paid', 'settle') and curr.operate_type in ('interest', 'pay_interest') else 0.0),
                    'pending_damages': prev.get('pending_damages') + (
                        curr.amount if bill.state not in ('paid', 'settle') and curr.operate_type in ('damages') else 0.0),
                    'fee': prev.get('fee') + (
                        curr.amount if bill.state not in ('paid', 'settle') and curr.operate_type in ('fee') else 0.0),
                }, bill.bill_log_ids, {
                    'freeze_quota': 0.0,
                    'used_quota': 0.0,
                    'loan_amount': 0.0,
                    'repayment_amount': 0.0,
                    'pending_amount': 0.0,
                    'pending_interest': 0.0,
                    'pending_damages': 0.0,
                    'fee': 0.0,
                }))

            bill.update({
                'pending_amount': bill.pending_amount if bill.pending_amount > 0 else 0.0,
            })

    # @api.depends('interest_ids', 'interest_ids.interest_amount')
    # def _compute_interest_info(self):
    #     for bill in self:
    #         bill.update({
    #             'interest_id': False,
    #             'is_overdue': False,
    #             'overdue_days': 0,
    #         })

    #         if bill.interest_ids.exists():
    #             bill.interest_id = bill.interest_ids[0]
    #             if bill.state == 'overdue' and bill.interest_id.interest_amount > 0:
    #                 bill.update({
    #                     'is_overdue': True,
    #                     'overdue_days': len(bill.interest_id.interest_log_ids.ids),
    #                 })

    def _generate_bill_code(self, repayment_date, cut_off_time, sub_loan_account, group_by_month, start_bill_date):
        current_repayment_date = repayment_date + timedelta(hours=cut_off_time)

        local_start_bill_date = fields.Datetime.context_timestamp(self, start_bill_date)
        code = ''.join([
            str(local_start_bill_date.year),
            '%02d' % local_start_bill_date.month])

        if group_by_month and start_bill_date:
            current_bill_date = local_to_utc(self, (local_start_bill_date + relativedelta(months=1)))
        else:
            # 这里先默认账单日为还款日往前推5天，后继看是否需要做为设置项
            current_bill_date = current_repayment_date - timedelta(days=5)

        record_bill = False
        if group_by_month:
            record_bill = self.search([('sub_loan_account_id', '=', sub_loan_account.id), ('code', '=', code)])
        else:
            code_count = self.search_count([
                ('code', '=like', code + '%')
            ])

            code = '%s%03d' % (code, code_count + 1)


        # 实际的还款日，需要在约定日期上，增加一天
        # 即约定10日还款，日切时间为一点半，则计算出来的还款日为 某年某月10日 1:30分，
        # 加一天后，实际为 某年某月11日 1:30分，以符合正常的认知
        current_repayment_date += timedelta(days=1)

        return record_bill, code, current_bill_date, current_repayment_date

    def daliy_cut_off(self):
        has_overdue = False
        bill_list_map = {}
        current_time = fields.Datetime.now()
        overdue_bill_ids: list[int] = []
        for bill in self:
            is_push = False
            if bill.state == 'current' and current_time >= bill.bill_date:
                '''
                当期账单需要检查一下是否已到账单日
                如果不是，算了；如果是，执行下面操作：
                1. 如果已用额度大于零，更新此账单状态为pending，把已用额度记为账单金额； 不然账单状态转为 paid
                2. 把 已用额度 写入到 账单金额
                '''
                is_push = True
                local_start_bill_date = fields.Datetime.context_timestamp(self, bill.start_bill_date)
                code = ''.join([
                    str(local_start_bill_date.year),
                    '%02d' % local_start_bill_date.month])
                group_by_month = bool(code == bill.code)

                fee_solution = bill.sub_loan_account_id.sudo().factor_supplier_id.fee_solution_id
                # 待还本金 = 本期已用金额 + 还之前账单时产生的溢缴款(有溢缴款为负数)
                bill_amount = bill.pending_amount if bill.pending_amount > 0 else 0.0
                fee = fee_solution.calc_amount_fee(bill.sub_loan_account_id.sudo().factor_supplier_id, bill_amount) if fee_solution else 0.0
                self.insert_bill(
                    sub_loan_account=bill.sub_loan_account_id, order_id=bill, operate_type='fee', 
                    amount=fee, group_by_month=group_by_month, start_bill_date=bill.start_bill_date, repayment_date=bill.repayment_date)
                bill.write({
                    'state': 'pending' if bill.pending_amount > 0 else 'paid',
                    # 如果未还金额大于0，账单金额为
                    'bill_amount': bill_amount,
                })

                next_start_bill_date = local_to_utc(self, local_start_bill_date + relativedelta(months=1))
                next_repayment_date = local_to_utc(self, (
                    local_start_bill_date + relativedelta(months=1) + relativedelta(months=bill.sub_loan_account_id.credit_term)
                    + relativedelta(days=(bill.sub_loan_account_id.repay_day - 1))
                ))
                # 冻结额度结转到下一期
                if bill.freeze_quota > 0:
                    order_ids = []
                    bill_log_ids = sorted(bill.bill_log_ids, key=lambda bill_log_id: bill_log_id.create_date,reverse=True)
                    for bill_log in bill_log_ids:
                        if bill_log.order_id.id in order_ids or bill_log.operate_type != 'freeze':
                            continue
                        order_ids.append(bill_log.order_id.id)
                        self.insert_bill(sub_loan_account=bill.sub_loan_account_id, order_id=bill_log.order_id,group_by_month=group_by_month,
                                         operate_type='unfreeze', amount=-bill_log.amount, remark='释放额度，移至下期', prev_log=bill_log,repayment_date=bill.repayment_date,start_bill_date=bill.start_bill_date)
                        new_bill_log = self.insert_bill(sub_loan_account=bill.sub_loan_account_id, order_id=bill_log.order_id, operate_type='freeze', amount=bill_log.amount,
                                         start_bill_date=next_start_bill_date, repayment_date=next_repayment_date, group_by_month=group_by_month, remark='上期结转，冻结额度', prev_log=bill_log)
                        if bill_log.order_id._name == 'ifs.gar.trade.list':
                            bill_log.order_id.sudo().write({
                                'bill_id':new_bill_log.bill_id.id,
                                'bill_log_id':new_bill_log.id
                            })
                # 如果存在溢缴款，则写入溢缴款到下一期账单 （当前时间这期）
                if bill.pending_amount < 0:
                    self.insert_bill(
                        sub_loan_account=bill.sub_loan_account_id, order_id=False, operate_type='balance',
                        amount=bill.pending_amount, group_by_month=group_by_month, 
                        start_bill_date=next_start_bill_date, repayment_date=next_repayment_date)
            elif bill.state == 'pending' and current_time >= bill.repayment_date:
                '''
                检查一下是否已到还款日
                如果未到，算了； 如果到了，执行下面操作
                1. 更新此账单状态为 overdue
                2. 计算利息
                '''
                bill.state = 'overdue'
                overdue_bill_ids.append(bill.id)
                self.env['ifs.gar.loan.account.interest'].do_interest(bill)
                has_overdue = True
                is_push = True
            elif bill.state == 'overdue':
                '''
                持续计算利息
                '''
                self.env['ifs.gar.loan.account.interest'].do_interest(bill)
                has_overdue = True
                is_push = True
            trade_list = self.env['ifs.gar.trade.list'].sudo().search([('bill_id','=', bill.id)])

            if is_push and trade_list.exists():
                open_app_id = self.env['galaxy.open.api.app'].sudo().search([('owner_id','=', f'ifs.partner.supplier,{bill.supplier_id.id}')],limit=1,order='create_date DESC')
                if open_app_id.exists():
                    bill_item = {
                        'merchant_code': bill.merchant_id.seq_code,
                        'bill_code': bill.code,
                        'state': bill.state,
                        'start_bill_date': bill.start_bill_date.strftime("%Y-%m-%d"),
                        'bill_date': bill.bill_date.strftime("%Y-%m-%d"),
                        'repayment_date': bill.repayment_date.strftime("%Y-%m-%d"),
                        'bill_amount': int(bill.bill_amount if bill.bill_amount != 0 else 0),
                        'damages': int(bill.pending_damages if bill.pending_damages != 0 else 0),
                        'interest': int(bill.pending_interest if bill.pending_interest != 0 else 0),
                        'repayment_amount': int(bill.repayment_amount if bill.repayment_amount != 0 else 0),
                        'pending_amount': int(bill.pending_amount if bill.pending_amount != 0 else 0),
                        'fee': int(bill.fee if bill.fee != 0 else 0),
                        'trade_list':[{
                                'supplier_code':trade_list_id.supplier_code,
                                'trade_code':trade_list_id.trade_code,
                                'trade_amount': int((trade_list_id.trade_amount - trade_list_id.reduce_amount)),
                                'trade_date': trade_list_id.trade_date.strftime("%Y-%m-%d"),
                                'remark':''
                            }for trade_list_id in trade_list],
                        # 'repayment_list':[]
                    }
                    bill_list = bill_list_map.get(open_app_id.id) if bill_list_map.get(open_app_id.id) else []
                    bill_list.append(bill_item)
                    bill_list_map[open_app_id.id] = bill_list
        # 每批发送的最大数量
        max_size = 10
        for open_app_id,bill_list in bill_list_map.items():
            # 当前地址推送的总批次数
            batch = math.ceil(len(bill_list) / max_size) 
            for i in range(0,batch):
                start_index = i * max_size
                current_batch = bill_list[start_index:start_index+max_size]
                self.env['ifs.message'].sudo().create({
                    'open_app_id':open_app_id,
                    'message_type':'bill',
                    'message_body':{
                        'bill_list':current_batch
                    }
                })
               
        cron = self.env['ir.cron'].sudo().env.ref(
            'ifs_gar_entry.push_all')
        self.env['ir.cron.trigger'].sudo().create(
            {'cron_id': cron.id, 'call_at': datetime.now() + relativedelta(seconds=30)}
        ) 
        if overdue_bill_ids:
            collection_order_model: InclusiveFinancingCollectionOrder = self.env['ifs.gar.collection.order']
            collection_order_model.create_collection_order_by_overdue_bills(overdue_bill_ids)
        return has_overdue

    def insert_bill(
            self, sub_loan_account, order_id, operate_type, amount, remark=False,
            record_bill=False, start_bill_date=False, repayment_date=False, prev_log=False, currency_id=False, group_by_month=False):
        '''
        动支操作
        参数：给出一个贷款主体方（买方与供应方的一条路由对象），操作类型和金额
        根据当前时间，以及订单设定的还款时间，生成一条账单记录，然后记账
        '''
        currency_id = currency_id or sub_loan_account.currency_id
        current_time = fields.Datetime.now()
        cut_off_time = sub_loan_account.sudo().factor_supplier_id.cut_off_time

        if not record_bill:
            record_bill, code, current_bill_date, current_repayment_date = self._generate_bill_code(
                repayment_date, cut_off_time,sub_loan_account, group_by_month, start_bill_date)
            if not record_bill:
                record_bill = self.create({
                    'code': code,
                    'sub_loan_account_id': sub_loan_account.id,
                    'cut_off_time': cut_off_time,
                    'start_bill_date': start_bill_date,
                    'bill_date': current_bill_date,
                    'repayment_date': current_repayment_date,
                    'currency_id': currency_id.id,
                })
        # elif record_bill.state == 'current' and operate_type in ('repayment', 'fuse'):
        #     # 如果在当前账单上还款，先把当前账单状态改为 pending，记入账单金额
        #     record_bill.write({
        #         'state': 'pending',
        #         'bill_amount': (record_bill.pending_amount + record_bill.fee) if record_bill.pending_amount > 0 else 0.0,
        #     })
        elif record_bill.state != 'current' and operate_type in ('freeze', 'loan', 'withdrawal'):
            # 如果此账单不是当前账单，即已出账或还款后的账单，不允许再上面用款
            raise UserError(_('此期账单已出，无法完成交易！'))

        if amount != 0:
            if amount > sub_loan_account.available_quota:
                raise UserError(_('可用额度不足，无法完成交易！'))

            bill_log_date = fields.Datetime.context_timestamp(
                self, current_time)
            today_cut_off_time_local = fields.Datetime.context_timestamp(
                self, current_time).replace(hour=0, minute=0, second=0) + timedelta(hours=cut_off_time)
            if bill_log_date >= today_cut_off_time_local:
                bill_log_date += timedelta(days=1)
            bill_log = self.env['ifs.gar.loan.account.bill.log'].create({
                'bill_id': record_bill.id,
                'order_id': '%s,%i' % (order_id._name, order_id.id),
                'operate_type': operate_type,
                'amount': amount,
                'remark': remark,
                'bill_log_date': bill_log_date,
                'prev_log_id': prev_log and prev_log.id,
            })

            return bill_log

        return False

    def is_bill_paided(self):
        self.ensure_one()
        if self.state in ['paid', 'plan', 'settle']:
            return True
        elif self.used_quota == 0 and self.state != 'current':
            self.state = 'paid'
            return True

        return False

    # def view_loan_account(self):
    #     self.ensure_one()

    #     return {
    #         'name': '贷款账户',
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'ifs.gar.loan.account',
    #         'res_id': self.loan_account_id.id,
    #         'target': 'new',
    #         'flags': {'mode': 'readonly'}
    #     }


class InclusiveFinancingLoanAccountBillLog(models.Model):
    _name = 'ifs.gar.loan.account.bill.log'
    _inherit = ['ifs.ir.sequence.mixin']
    _description = '保理账户的额度操作记录'
    _order = 'seq_code desc, write_date desc'
    _rec_name = 'seq_code'

    bill_id = fields.Many2one(
        'ifs.gar.loan.account.bill', string='所属账单', required=True)
    order_id = fields.Reference(
        selection=[('ifs.gar.loan.account.bill', '手续费')], string='关联单据', ondelete='set null')
    # supplier_id = fields.Many2one(
    #     'ifs.partner.supplier',
    #     string='供应商', compute='_compute_supplier_id')

    currency_id = fields.Many2one(related='bill_id.currency_id')
    operate_type = fields.Selection([
        ('freeze', '冻结'),
        ('unfreeze', '解冻'),
        ('loan', '动支'),
        ('refund', '退款'),
        ('repayment', '还款'),
        ('payment_plan', '分期'),
        ('withdrawal', '提款'),
        ('fuse', '熔断'),
        ('interest', '计息'),
        ('damages', '违约金'),
        ('pay_interest', '付息'),
        ('fee', '手续费'),
    ], string='操作类型', required=True, readonly=True)

    amount = fields.Monetary('发生金额', required=True, readonly=True)
    remark = fields.Char('操作备注')
    bill_log_date = fields.Date(string='记账日期', required=True, readonly=True)
    prev_log_id = fields.Many2one(
        'ifs.gar.loan.account.bill.log', string='前一条操作记录')

    # @api.depends('order_id')
    # def _compute_supplier_id(self):
    #     for record in self:
    #         record.supplier_id = record.order_id.supplier_id
