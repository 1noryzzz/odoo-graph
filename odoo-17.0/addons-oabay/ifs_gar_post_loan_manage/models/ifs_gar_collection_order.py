# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from typing import TYPE_CHECKING, cast

import json
from datetime import timedelta

if TYPE_CHECKING:
    from odoo.addons.ifs_gar_account.models.ifs_gar_loan_account_bill import InclusiveFinancingLoanAccountBill


class InclusiveFinancingCollectionOrder(models.Model):
    _name = 'ifs.gar.collection.order'
    _description = '催收单据'
    _order = 'create_date desc, id desc'
    _rec_name = 'seq_code'

    _sql_constraints = [
        ('bill_unique', 'unique(bill_id)', '该账单已创建催收单据'),
    ]

    seq_code = fields.Char('催收单号', required=True, readonly=True, default=lambda self: _('New'))

    bill_id = fields.Many2one(
        'ifs.gar.loan.account.bill',
        string='关联账单',
        required=True,
        ondelete='restrict',
        domain="[('state', '=', 'overdue')]",
    )

    bill_code = fields.Char('账单编号', related='bill_id.code', store=True, readonly=True)
    bill_date = fields.Datetime('账单日', related='bill_id.bill_date', store=True, readonly=True)
    repayment_date = fields.Datetime('还款日', related='bill_id.repayment_date', store=True, readonly=True)
    overdue_days = fields.Integer('逾期天数', compute='_compute_overdue_days', store=True)
    overdue_stage = fields.Selection(related='bill_id.state', string='逾期阶段', store=True, readonly=True)
    repayment_amount = fields.Monetary('已还金额', related='bill_id.repayment_amount', store=True, readonly=True)
    bill_amount = fields.Monetary('账单金额', related='bill_id.bill_amount', store=True, readonly=True)
    pending_amount = fields.Monetary('待还金额', compute='_compute_pending_amount', store=True)

    merchant_id = fields.Many2one('ifs.partner.merchant', string='采购方', related='bill_id.merchant_id', store=True, readonly=True)
    merchant_code = fields.Char('采购商编号', related='merchant_id.seq_code', store=True, readonly=True)
    merchant_name = fields.Char('采购方名称', related='merchant_id.name', store=True, readonly=True)
    legal_name = fields.Char('法人姓名', related='bill_id.legal_name', store=True, readonly=True)

    approval_date = fields.Date('授信时间', related='bill_id.sub_loan_account_id.t18_contract_info_id.sign_date', store=True, readonly=True)
    expire_date = fields.Date('合同到期时间', related='bill_id.sub_loan_account_id.t18_contract_info_id.expire_date', store=True, readonly=True)
    approve_quota = fields.Monetary('授信额度', related='bill_id.sub_loan_account_id.approved_quota', store=True, readonly=True)
    used_quota = fields.Monetary('已用额度', related='bill_id.sub_loan_account_id.used_quota', store=True, readonly=True)
    available_quota = fields.Monetary('可用额度', related='bill_id.sub_loan_account_id.available_quota', store=True, readonly=True)

    is_rollover = fields.Boolean('是否展期', default=False)
    fact_state = fields.Selection([
        ('not_started', '未发起'),
        ('started', '已发起'),
        ('done', '已完成'),
    ], string='保理放款状态', default='not_started', required=True)
    guarantee_state = fields.Selection([
        ('not_started', '未发起'),
        ('started', '已发起'),
        ('done', '已完成'),
    ], string='担保代偿状态', default='not_started', required=True)
    is_bad_debt = fields.Boolean('是否坏账', default=False)
    is_special_state = fields.Boolean('特殊状态', default=False)

    currency_id = fields.Many2one('res.currency', related='bill_id.currency_id', store=True, readonly=True)
    default_rollover_days = fields.Integer("默认展期天数", default=15)
    factoring_record_ids = fields.One2many('ifs.gar.factoring.record', 'collection_order_id', string='保理放款记录')

    @api.depends('repayment_date')
    def _compute_overdue_days(self):
        for record in self:
            record.overdue_days = 0
            if not record.repayment_date:
                continue
            today = fields.Date.context_today(record)
            repayment_day = fields.Datetime.context_timestamp(record, record.repayment_date).date()
            record.overdue_days = max((today - repayment_day).days, 0)

    @api.depends('bill_id.pending_amount', 'bill_id.pending_interest')
    def _compute_pending_amount(self):
        for record in self:
            record.pending_amount = (record.bill_id.pending_amount or 0.0) + (record.bill_id.pending_interest or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('seq_code', _('New')) == _('New'):
                vals['seq_code'] = self.env['ir.sequence'].next_by_code('ifs.gar.collection.order') or _('New')
        return super().create(vals_list)

    @api.model
    def create_collection_order_by_overdue_bills(self, overdue_bill_ids: list[int]):
        if not overdue_bill_ids:
            return self.browse()

        # 幂等处理：去重后仅处理仍处于逾期状态的账单。
        candidate_bill_ids = list(set(overdue_bill_ids))
        bill_model: InclusiveFinancingLoanAccountBill = self.env['ifs.gar.loan.account.bill']
        overdue_bills = bill_model.search([
            ('id', 'in', candidate_bill_ids),
            ('state', '=', 'overdue'),
        ])
        if not overdue_bills:
            return self.browse()

        # 幂等处理：过滤已存在催收单的账单，避免唯一约束冲突中断批次。
        exist_orders = self.search([('bill_id', 'in', overdue_bills.ids)])
        exist_bill_ids = set(exist_orders.mapped('bill_id').ids)
        to_create_bill_ids = [bill_id for bill_id in overdue_bills.ids if bill_id not in exist_bill_ids]
        if not to_create_bill_ids:
            return self.browse()

        return self.create([{'bill_id': bill_id} for bill_id in to_create_bill_ids])

    def action_open_detail(self):
        self.ensure_one()
        form_view = self.env.ref('ifs_gar_post_loan_manage.ifs_gar_collection_order_view_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('催收详情'),
            'res_model': 'ifs.gar.collection.order',
            'view_mode': 'form',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'current',
        }

    def _show_todo_notification(self, action_name):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('功能预留'),
                'message': _('%s功能后续将调用第三方接口，当前版本暂未接入。') % action_name,
                'sticky': False,
                'type': 'warning',
            },
        }

    def _show_execute_success(self, action_name):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('执行成功'),
                'message': _('%s执行成功。') % action_name,
                'sticky': False,
                'type': 'success',
            },
        }

    def action_sign_rollover(self):
        self.ensure_one()
        if not self.is_rollover:
            # 生成展期合同
            bill = self.bill_id
            start_bill_date_local = fields.Datetime.context_timestamp(bill, bill.start_bill_date)
            bill_date_local = fields.Datetime.context_timestamp(bill, bill.bill_date)
            end_bill_date_local = bill_date_local - timedelta(days=1)
            repayment_date_local = (
                fields.Datetime.context_timestamp(bill, bill.repayment_date)
                - timedelta(days=1)
                + timedelta(days=self.default_rollover_days)
            )
            params = json.dumps({
                "t24_contract_code": str(bill.t24_contract_info_id.code),
                "bill_code": str(bill.code),
                "bill_amount": str(bill.bill_amount),
                "bill_cycle": f'{start_bill_date_local.strftime("%Y年%m月%d日")} - {end_bill_date_local.strftime("%Y年%m月%d日")}',
                "bill_day": bill_date_local.strftime("%Y年%m月%d日"),
                "repayment_day": repayment_date_local.strftime("%Y年%m月%d日"),
            })
            t24_template = self.env["ifs.contract.template"].retrieve_by_code(
                "T24", bill.factor_id.id, bill.supplier_id.id
            )
            t24_contract_info = self.env["ifs.contract.info"].create({
                "name": t24_template.name,
                "partner_one": "%s,%d" % (bill.merchant_id._name, bill.merchant_id.id),
                "partner_two": "%s,%d" % (bill.factor_id._name, bill.factor_id.id),
                "template_id": t24_template.id,
                "params": params,
                "partner_one_signature": bill.merchant_id.signature,
                "partner_two_signature": bill.factor_id.signature,
            })
            # 关联账单 并签约
            bill.t24_contract_info_id = t24_contract_info
            bill.t24_contract_info_id.signature_all()
            self.is_rollover = True
            return self._show_execute_success(_('签署展期'))
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('已签署展期'),
                    'message': _('无需重复操作'),
                    'sticky': False,
                    'type': 'warning',
                },
            }

    def action_start_factoring(self):
        self.ensure_one()
        if self.fact_state == 'not_started':
            self.fact_state = 'started'
            return self._show_execute_success(_('发起保理'))
        if self.fact_state == 'started':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('已发起保理'),
                    'message': _('无需重复操作'),
                    'sticky': False,
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('保理已完成'),
                'message': _('当前单据已完成保理放款'),
                'sticky': False,
                'type': 'warning',
            },
        }

    @api.model
    def query_factoring_payment_orders(self, project_code: str, request_date: str):
        orders = self.search([('fact_state', '=', 'started')], order='id asc')
        return {
            'transaction_code': self.seq_code,
            'project_code': project_code,
            'request_date': request_date,
            'business_details': [order._to_factoring_business_detail() for order in orders],
        }

    def _to_factoring_business_detail(self):
        self.ensure_one()
        factor = self.bill_id.factor_id
        supplier = self.bill_id.supplier_id
        factor_company = factor.ifs_company_id
        supplier_company = supplier.ifs_company_id
        return {
            'fact_name': factor.name or '',
            'payment_info': {
                'payment_time': fields.Date.context_today(self).strftime('%Y-%m-%d'),
                'fact_amount': self.pending_amount,
                'deduction_amount': self.pending_amount,
                'request_pay_amount': self.pending_amount,
                'payer_account': factor_company.account_no or '',
                'payer_company': factor.name or '',
                'payer_bank': factor_company.deposit_bank or '',
                'payee_account': supplier_company.account_no or '',
                'payee_company': supplier.name or '',
                'payee_bank': supplier_company.deposit_bank or '',
                'payment_currency': (self.currency_id.name or 'CNY') if self.currency_id else 'CNY',
                'payment_type': '银行转账',
            },
            'buyer_name': self.merchant_name or '',
            'contract_info': [
                {
                    'contract_name': self.bill_id.t20_contract_info_id.name
                    if self.bill_id.t20_contract_info_id
                    else '',
                    'url': '',
                }
            ],
        }

    @api.model
    def update_factoring_payment_order(
        self,
        transaction_code: str,
        payment_time: str,
        actual_payment_amount: float,
        payment_voucher: str,
    ):
        order = self.search([('seq_code', '=', transaction_code)], limit=1)
        if not order:
            return {'transaction_code': transaction_code, 'error_msg': '未找到对应逾期单据编码'}
        if order.fact_state != 'started':
            return {'transaction_code': transaction_code, 'error_msg': '当前状态不允许更新付款申请单'}

        order.fact_state = 'done'
        order.env['ifs.gar.factoring.record'].create({
            'collection_order_id': order.id,
            'factor_id': order.bill_id.factor_id.id,
            'supplier_id': order.bill_id.supplier_id.id,
            'payment_time': payment_time,
            'actual_payment_amount': actual_payment_amount,
            'payment_voucher': str(payment_voucher or ''),
        })
        return {
            'transaction_code': order.seq_code,
            'fact_state': order.fact_state,
            'error_msg': '',
        }

    def action_start_guarantee(self):
        self.ensure_one()
        return self._show_todo_notification(_('发起代偿'))

    def action_mark_bad_debt(self):
        self.ensure_one()
        return self._show_todo_notification(_('认定坏账'))
