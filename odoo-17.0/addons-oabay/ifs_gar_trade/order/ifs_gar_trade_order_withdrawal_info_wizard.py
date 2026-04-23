# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

from ..models.ifs_gar_trade_order import CREDIT_TERM


class GuaranteeAccountsRecvTradeOrderWithdrawalInfoWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.withdrawal.info.wizard'
    _inherit = 'ifs.gar.order.step'
    _description = '提款信息录入向导'

    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)

        if 'order_info_definition_id' in default_fields:
            trade_order_id = self.env.context.get('default_trade_order_id')
            trade_order = self.env['ifs.gar.trade.order'].browse(
                trade_order_id)
            cdetails = self.env['ifs.gar.trade.order.config'].retrieve_config(
                trade_order.factor_id.id, trade_order.supplier_id.id, ['TKXXLL'])
            cdetail = cdetails.filtered(lambda c: c.code == 'TKXXLL')
            if cdetail.is_visible:
                defaults.update({
                    'order_info_config_detail_id': cdetail.id,
                    'order_info_definition_id': cdetail.definition_id.id,
                    'order_info_is_required': cdetail.is_required,
                    'order_info_is_visible': cdetail.is_visible,
                })

        if 'trade_order_id' in default_fields:
            trade_order = self.env['ifs.gar.trade.order'].browse(
                defaults.get('trade_order_id'))
            defaults.setdefault('order_code', trade_order.order_code)
            defaults.setdefault('trade_amount', trade_order.trade_amount)
            defaults.setdefault('withdrawal_amount',
                                trade_order.withdrawal_amount)
            defaults.setdefault('trade_date', trade_order.trade_date)
            defaults.setdefault('trade_start_date', trade_order.trade_start_date)
            defaults.setdefault('credit_term', trade_order.credit_term)
            defaults.setdefault('delivery_remark', trade_order.delivery_remark)

        return defaults

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', string='交易订单', required=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='trade_order_id.merchant_id')
    currency_id = fields.Many2one(
        'res.currency', related='trade_order_id.currency_id')

    merchant_code = fields.Char('采购方编号', related="merchant_id.seq_code")
    merchant_name = fields.Char('采购方名称', related="merchant_id.name")
    merchant_approved_quota = fields.Monetary(
        "授信额度", compute='_compute_quota_info')  # 此处直接用关联字段存在问题，没有过滤掉当前采购方在其他方的相关额度信息，所以使用计算字段，同时其他额度信息也会变正常
    merchant_available_quota = fields.Monetary(
        "可用额度", related='merchant_id.available_quota')
    merchant_used_quota = fields.Monetary(
        "已用额度", related='merchant_id.used_quota')

    order_code = fields.Char(
        string='基础合同编号', copy=False, required=True)
    trade_amount = fields.Monetary('基础合同金额', required=True)
    withdrawal_amount = fields.Monetary("本次提款金额", required=True)
    trade_date = fields.Date(
        '合同签署日期', required=True, default=lambda self: fields.Date.today())
    trade_start_date = fields.Date(
        '账期起始日', required=True, default=lambda self: fields.Date.today())
    delivery_remark = fields.Text('交货情况说明')

    credit_term = fields.Integer(
        "账期设定(天)", help='账期，单位为天', default=90, required=True)
    repayment_date = fields.Date(
        string='还款日', compute="_compute_credit_term")
    days_left = fields.Integer("剩余天数", compute="_compute_credit_term")

    item_ids = fields.One2many(
        'ifs.gar.trade.order.item', related='trade_order_id.item_ids', string='订单明细', readonly=False, required=True)

    order_info_config_detail_id = fields.Many2one(
        'ifs.gar.trade.order.config.detail', string='交易订单配置id')
    order_info_definition_id = fields.Many2one(
        'ifs.gar.trade.definition', string='交易订单配置id')
    order_info_is_required = fields.Boolean('是否必填', default=False)
    order_info_is_visible = fields.Boolean('是否可见', default=False)
    order_info = fields.Properties(
        '交易订单相关信息', definition='order_info_definition_id.params_definition')

    @api.depends('merchant_id')
    def _compute_quota_info(self):
        for record in self:
            if record.merchant_id:
                record.merchant_approved_quota = record.merchant_id.approved_quota
            else:
                record.merchant_approved_quota = False

    @api.depends('trade_start_date', 'credit_term')
    def _compute_credit_term(self):
        for record in self:
            if record.trade_start_date and record.credit_term:
                record.repayment_date = record.trade_start_date + \
                    relativedelta(days=record.credit_term)
                record.days_left = record.repayment_date.__sub__(
                    record.trade_start_date).days
            else:
                record.repayment_date = False
                record.days_left = False

    def action_next(self):
        if self.withdrawal_amount <= 0:
            raise UserError(_('请输入正确的提款金额！'))

        if not self.trade_order_id.item_ids:
            raise UserError(_('交易清单不能为空！'))
        err_msgs = self.order_info_config_detail_id.validate_required(
            self.order_info)
        if len(err_msgs) > 0:
            raise ValidationError(
                _(f'请填写附加信息！包含下列内容：\n\n{"，".join(err_msgs)}'))
        order_info = self.read(
            ['order_code', 'trade_amount', 'withdrawal_amount', 'trade_date', 'trade_start_date', 'delivery_remark', 'credit_term'])[0]
        order_info.pop('id')
        order_info.update({
            'order_info_definition_id': self.order_info_definition_id.id,
            'order_info': self.order_info
        })

        self.trade_order_id.write(order_info)

        if self.has_next_step:
            return super().action_next()
        else:
            return self.trade_order_id.pre_confirm_order()

    def action_approved_quota(self):
        self.ensure_one()
        sub_loan_account_id = self.env['ifs.gar.sub.loan.account'].search(
            [('supplier_id', '=', self.trade_order_id.supplier_id.id), ('merchant_id', '=', self.merchant_id.id)])
        if sub_loan_account_id:
            return {
                'name': _('子账户列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.sub.loan.account',
                'res_id': False,
                'domain': [('id', '=', sub_loan_account_id.id)],
                'target': 'new',
            }

    def action_available_quota(self):
        self.ensure_one()
        if self.merchant_id:
            return {
                'name': _('订单列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.trade.order',
                'res_id': False,
                'domain': [('merchant_id', '=', self.merchant_id.id)],
                'target': 'new',
            }

    def action_used_quota(self):
        pass
