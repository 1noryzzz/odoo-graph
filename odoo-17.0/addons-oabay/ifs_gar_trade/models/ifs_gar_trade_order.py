# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError

CREDIT_TERM = [
    ('1', '1个月'),
    ('2', '2个月'),
    ('3', '3个月'),
    ('4', '4个月'),
    ('5', '5个月'),
    ('6', '半年'),
    ('12', '一年'),
]


class GuaranteeAccountsRecvTradeOrder(models.Model):
    _name = 'ifs.gar.trade.order'
    _description = '交易信息'
    _inherit = [
        'mail.thread', 'mail.activity.mixin', 'ifs.ir.sequence.mixin',
        'ifs.step.by.step.mixin', 'ifs.currency.rmb.mixin']
    _rec_name = 'seq_code'
    _ref_id_field = 'trade_order_id'
    _order = 'create_date desc'

    def _step_models(self):
        return [
            'ifs.gar.trade.order.merchant.info.wizard',
            'ifs.gar.trade.order.withdrawal.info.wizard',
        ]

    state = fields.Selection(
        string='订单状态', selection=[
            ('draft', '草稿'),
            ('pending', '待确认'),
            ('rejected', '已拒绝'),
            ('confirmed', '已确认'),
            ('repaid', '已还款'),
            ('settle', '已结清'),
        ], readonly=True,
        copy=False, index=True, tracking=True, default='draft')

    order_code = fields.Char(
        string='基础合同编号', copy=False, tracking=True)
    trade_amount = fields.Monetary('基础合同金额', tracking=True)
    withdrawal_amount = fields.Monetary("本次提款金额", tracking=True)
    withdrawal_amount_uppercase = fields.Char(
        "提款金额大写", compute="_compute_withdrawal_amount_uppercase")
    trade_date = fields.Date(
        '合同签署日期', required=True, default=lambda self: fields.Date.today())
    trade_start_date = fields.Date(
        '账期起始日', required=True, default=lambda self: fields.Date.today())
    delivery_remark = fields.Text('交货情况说明')
    order_info_definition_id = fields.Many2one(
        'ifs.gar.trade.definition', string='交易订单额外信息配置', readonly=True)
    order_info = fields.Properties(
        '交易订单相关信息', definition='order_info_definition_id.params_definition')

    credit_term = fields.Integer(
        "账期设定(天)", help='账期，单位为天', default=90, required=True)
    repayment_date = fields.Date(
        string='还款日', compute="_compute_credit_term")
    days_left = fields.Integer("剩余天数", compute="_compute_credit_term")

    item_ids = fields.One2many(
        'ifs.gar.trade.order.item', 'trade_order_id', string='订单明细')

    sub_loan_account_id = fields.Many2one(
        'ifs.gar.sub.loan.account', ondelete='restrict', string='贷款账户')
    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', related='sub_loan_account_id.loan_account_id.factor_id', store=True)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', related='sub_loan_account_id.supplier_id', store=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='sub_loan_account_id.merchant_id', store=True)

    account_name = fields.Char(
        '收款账户', related='factor_id.account_name')
    account_no = fields.Char(
        '收款账号', related='factor_id.account_no')
    deposit_bank = fields.Char(
        '开户银行', related='factor_id.deposit_bank')
    supplier_code = fields.Char('供应方编号', related="supplier_id.seq_code")
    merchant_code = fields.Char('采购方编号', related="merchant_id.seq_code")
    definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='采购方信息定义', related='merchant_id.definition_id')
    json_datas = fields.Properties(
        '采购方信息', definition='definition_id.params_definition', related='merchant_id.json_datas')
    key_person_ids = fields.One2many(
        'ifs.base.company.detail', string='主要人员', related='merchant_id.key_person_ids')
    merchant_approved_quota = fields.Monetary(
        "授信额度", compute='_compute_quota_info')#此处直接用关联字段存在问题，没有过滤掉当前采购方在其他方的相关额度信息，所以使用计算字段，同时其他额度信息也会变正常
    merchant_available_quota = fields.Monetary(
        "可用额度", related='merchant_id.available_quota')
    merchant_used_quota = fields.Monetary(
        "已用额度", related='merchant_id.used_quota')
    merchant_quota_state = fields.Selection(
        "额度状态", related='sub_loan_account_id.state')

    bill_id = fields.Many2one(
        'ifs.gar.loan.account.bill', string='记账账单', ondelete='restrict')
    # 记录下订单写入的最后一次关联日志，比如执行冻结额度的记录，
    # 供相应记录在解冻时操作
    bill_log_id = fields.Many2one(
        'ifs.gar.loan.account.bill.log', string='生效的关联日志')

    # company_id = fields.Many2one(
    #     'res.company', related='merchant_id.company_id')
    currency_id = fields.Many2one(
        'res.currency', string='币种', required=True,
        default=lambda self: self.env.user.company_id.currency_id)

    @api.depends('merchant_id')
    def _compute_quota_info(self):
        for record in self:
            if record.merchant_id:
                record.merchant_approved_quota = record.merchant_id.approved_quota
            else:
                record.merchant_approved_quota = False

    @api.depends('withdrawal_amount')
    def _compute_withdrawal_amount_uppercase(self):
        for record in self:
            record.withdrawal_amount_uppercase = record.upper_to_rmb(
                record.withdrawal_amount)

    @api.depends('trade_start_date', 'credit_term')
    def _compute_credit_term(self):
        for record in self:
            if record.trade_start_date and record.credit_term:
                record.repayment_date = record.trade_start_date + \
                    relativedelta(days=record.credit_term)
                record.days_left = record.repayment_date.__sub__(
                    fields.Date.today()).days
            else:
                record.repayment_date = False
                record.days_left = False
                
    def pre_confirm_order(self):
        self.ensure_one()
        return {
            'name': '确认交易订单',
            'view_mode': 'form',
            'res_model': 'ifs.gar.trade.order.withdrawal.confirm.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_trade_order_id': self.id,
            }
        }

    def confirm_order(self):
        self.ensure_one()
        if self.state == 'draft' and self.supplier_id.company_id.id == self.env.company.id:
            bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                self.sub_loan_account_id, self, 'freeze', self.withdrawal_amount,
                remark='交易订单提交，冻结额度', start_bill_date=self.trade_date, repayment_date=self.repayment_date)

            self.write({
                'state': 'pending',
                'bill_id': bill_log.bill_id,
                'bill_log_id': bill_log.id,
            })

            return {
                'name': self.env['ifs.gar.trade.order']._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form,list',
                'res_model': 'ifs.gar.trade.order',
                'views': [[False, 'list'], [False, 'form']],
                'res_id': self.id,
                'target': 'current',
                'context': {
                    'no_breadcrumbs': True,
                }
            }
        elif self.state == 'pending' and self.merchant_id.company_id.id == self.env.company.id:
            if self.bill_log_id and self.bill_log_id.operate_type == 'freeze':
                unfreeze_bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    self.sub_loan_account_id, self,
                    'unfreeze', -self.bill_log_id.amount, '交易已确立', record_bill=self.bill_id, prev_log=self.bill_log_id)

                bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    self.sub_loan_account_id, self, 'loan', self.withdrawal_amount,
                    remark='交易确认，使用额度', repayment_date=self.repayment_date, record_bill=self.bill_id, prev_log=unfreeze_bill_log)

                self.write({
                    'state': 'confirmed',
                    'bill_log_id': bill_log.id,
                })

                return {
                    'name': self.env['ifs.gar.trade.order']._description,
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                    'views': [[False, 'list'], [False, 'form']],
                    'res_model': 'ifs.gar.trade.order',
                    'res_id': False,
                    'target': 'current',
                    'context': {
                        'search_default_group_state': True,
                    }
                }
            else:
                raise UserError(_('数据错误，请联系管理员！'))

    def refuse_order(self):
        self.ensure_one()

        if self.state == 'pending' and self.merchant_id.company_id.id == self.env.company.id:
            if self.bill_log_id and self.bill_log_id.operate_type == 'freeze':
                bill_log = self.env['ifs.gar.loan.account.bill'].insert_bill(
                    self.sub_loan_account_id, self, 'unfreeze', -self.bill_log_id.amount, '交易拒绝，解冻额度', record_bill=self.bill_id, prev_log=self.bill_log_id)
                self.write({
                    'state': 'rejected',
                    'bill_log_id': bill_log.id,
                })

                return {
                    'name': self.env['ifs.gar.trade.order']._description,
                    'type': 'ir.actions.act_window',
                    'view_mode': 'list,form',
                    'views': [[False, 'list'], [False, 'form']],
                    'res_model': 'ifs.gar.trade.order',
                    'res_id': False,
                    'target': 'current',
                    'context': {
                        'search_default_group_state': True,
                    }
                }
            else:
                raise UserError(_('数据错误，请联系管理员！'))

    def view_trade_order(self):
        if self.state == 'draft' and self.supplier_id.company_id.id == self.env.company.id:
            return self.start_step()
        else:
            return {
                'name': self.env['ifs.gar.trade.order']._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.trade.order',
                'views': [[False, 'form']],
                'res_id': self.id,
                'target': 'current',
            }

    def selector_merchant(self):
        if 'supplier' not in (self.env.company.ifs_partners or []):
            raise AccessDenied(_('仅供应方可创建订单！'))

        supplier = self.env['ifs.partner.supplier'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not supplier.id:
            raise UserError(_('数据异常，请联系管理员！'))

        return {
            'name': '选择采购方',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'ifs.partner.merchant',
            'target': 'new',
            'domain': [('state', '=', 'normal')],
            'views': [
                [self.env.ref(
                    'ifs_gar_trade.ifs_partner_merchant_view_tree_order').id, 'tree']
            ],
            'context': {
                'trade_supplier_id': supplier.id,
            }
        }

    def start_trade_order(self, merchant_id):
        if not self.env.context.get('trade_supplier_id'):
            raise AccessDenied(_('无法创建订单，缺少供应商信息'))

        supplier_id = self.env.context.get('trade_supplier_id')
        sub_loan_account = self.env['ifs.gar.sub.loan.account'].search([
            ('supplier_id', '=', supplier_id),
            ('merchant_id', '=', merchant_id)
        ], limit=1)

        if sub_loan_account.id:
            return self.create({
                'sub_loan_account_id': sub_loan_account.id,
            }).start_step()
        else:
            raise UserError(_('采购方的贷款账户不存在！'))


class GuaranteeAccountsRecvTradeOrderItem(models.Model):
    _name = 'ifs.gar.trade.order.item'
    _description = '交易订单所附货物清单'
    _order = 'sequence'

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', string='交易订单', index=True, ondelete='cascade')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='trade_order_id.currency_id')
    sequence = fields.Integer('排序', required=True, default=40)
    name = fields.Char('商品名称', required=True)
    model = fields.Char('型号')
    quantity = fields.Integer('数量', required=True, default=1)
    price = fields.Monetary('单价', required=True, default=0.0)
    amount = fields.Monetary(compute='_compute_amount', string='金额')
    remark = fields.Char('备注')

    @api.depends('quantity', 'price')
    def _compute_amount(self):
        for item in self:
            item.amount = item.price * item.quantity
