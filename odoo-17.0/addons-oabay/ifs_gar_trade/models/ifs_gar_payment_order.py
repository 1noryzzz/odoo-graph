from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.galaxy_common.fields import local_to_utc


class GuaranteeAccountsRecvPaymentOrder(models.Model):
    _name = "ifs.gar.payment.order"
    _inherit = ["ifs.ir.sequence.mixin", "uuid.short.mixin"]
    _description = "支付订单信息"
    _rec_name = "seq_code"

    merchant_code = fields.Char("付款方商编")
    merchant_id = fields.Many2one(
        "ifs.partner.merchant",
        string="付款方",
        required=True,
        ondelete="restrict",
        auto_join=True,
        index=True,
    )
    pay_amount = fields.Monetary("支付金额")
    bill_id = fields.Many2one(
        "ifs.gar.loan.account.bill", string="记账账单", ondelete="restrict"
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("freeze", "冻结额度成功"),
            ("loan", "资方用信成功"),
            ("refund", "退款成功"),
            ("part_refund", "支付订单中业务订单发生退款"),
        ],
        string="支付状态",
        default="draft",
    )
    after_payment = fields.Char("支付后界面")
    url_type = fields.Selection(
        [("web", "网页"), ("wxmini", "小程序")], string="url类型", default="web"
    )
    token = fields.Char("订单token")
    expiration = fields.Datetime("token过期时间")
    token_valid = fields.Boolean(
        compute="_compute_token_valid", string="签名Token是否有效"
    )
    currency_id = fields.Many2one(
        "res.currency", string="币种", related="merchant_id.currency_id"
    )

    trade_list = fields.One2many(
        "ifs.gar.trade.list", "payment_id", string="交易订单列表"
    )

    @api.depends("token", "expiration")
    def _compute_token_valid(self):
        dt = fields.Datetime.now()
        for sign_token in self:
            sign_token.token_valid = bool(sign_token.token) and (
                not sign_token.expiration or dt <= sign_token.expiration
            )

    @api.model
    def create(self, vals):
        if "token" not in vals:
            token = self.short_uuid4()
            while self.sign_with_token(token):
                token = self.short_uuid4()
            vals["token"] = token

        vals["expiration"] = fields.Datetime.now() + timedelta(hours=2)
        order = super(GuaranteeAccountsRecvPaymentOrder, self).create(vals)

        return order

    def sign_with_token(self, token, check_validity=False, raise_exception=False):
        sign_token = self.search([("token", "=", token)], limit=1)
        if not sign_token:
            if raise_exception:
                raise UserError(_("签名参数无效"))
            return False
        if check_validity and not sign_token.token_valid:
            if raise_exception:
                raise UserError(_("签名Token过期"))
            return False
        return sign_token

    def freeze_order(self):
        bill_log = False
        for trade in self.trade_list:
            sub_loan_account_id = self.env["ifs.gar.sub.loan.account"].search(
                [
                    ("merchant_id.seq_code", "=", self.merchant_code),
                    ("supplier_id.seq_code", "=", trade.supplier_code),
                ]
            )

            # 交易时间当月1号的零点为此期账单的开始时间
            midnight_local = datetime.combine(trade.trade_date.replace(day=1), datetime.min.time())
            start_bill_date = local_to_utc(self, midnight_local)
            repayment_date = (
                start_bill_date
                + relativedelta(months=sub_loan_account_id.credit_term)
                + relativedelta(days=(sub_loan_account_id.repay_day - 1))
            )

            bill_log = self.env["ifs.gar.loan.account.bill"].insert_bill(
                sub_loan_account_id,
                trade,
                "loan", # 冻结额度改为动支
                trade.trade_amount - trade.reduce_amount,
                remark=f'订单号：{trade.trade_code}，交易金额：{trade.trade_amount}元',
                start_bill_date=start_bill_date,
                repayment_date=repayment_date,
                group_by_month=True,
            )

            trade.write(
                {
                    "state": "loan",# 冻结额度改为动支
                    "bill_log_id": bill_log.id,
                    "bill_id": bill_log.bill_id.id,
                }
            )

        self.write({
            "bill_id": bill_log.bill_id.id,
            "state": "loan",# 冻结额度改为动支
        })

class GuaranteeAccountsRecvTradeList(models.Model):
    _name = "ifs.gar.trade.list"
    _description = "交易订单列表"

    payment_id = fields.Many2one("ifs.gar.payment.order", string="支付订单")
    supplier_code = fields.Char("供应方商编")
    supplier_id = fields.Many2one(
        "ifs.partner.supplier",
        string="供应方",
        required=True,
        ondelete="restrict",
        auto_join=True,
        index=True,
    )
    trade_code = fields.Char("交易订单号")
    trade_amount = fields.Monetary("交易金额")
    reduce_amount = fields.Monetary("调整金额(调减)")
    final_amount = fields.Monetary("实付金额", compute="_compute_final_amount")
    trade_date = fields.Date("交易日期")
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("freeze", "冻结额度成功"),
            ("loan", "资方用信成功"),
            ("refund", "退款成功"),
        ],
        string="支付状态",
        default="draft",
    )
    currency_id = fields.Many2one(
        "res.currency", string="币种", related="payment_id.currency_id"
    )
    bill_id = fields.Many2one(
        "ifs.gar.loan.account.bill", string="记账账单", ondelete="restrict"
    )
    bill_log_id = fields.Many2one(
        "ifs.gar.loan.account.bill.log", string="生效的关联日志"
    )
    start_bill_date = fields.Datetime("账单开始日期", related="bill_id.start_bill_date")
    bill_date = fields.Datetime("记账日期", related="bill_id.bill_date")
    repayment_date = fields.Datetime("还款日期", related="bill_id.repayment_date")

    reduce_reasons = fields.Many2many(
        "ifs.gar.trade.reduce.reasons",
        "ifs_gar_trade_list_reduce_reasons_rel",
        "trade_list_id",
        "reduce_reason_id",
        string="调整理由",
    )
    reduce_reson_desc = fields.Html("调整说明")

    receipt_code = fields.Char("物流单号")
    own_trans = fields.Boolean("是否自有物流", default=False)
    receipted_order = fields.Boolean("是否已收货", default=False)
    canceled = fields.Boolean("是否已取消", default=False)

    @api.constrains("trade_code", "state")
    def _check_trade_code(self):
        for trade in self:
            trade_list = self.search(
                [("trade_code", "=", trade.trade_code), ("state", "!=", "draft")]
            )
            if len(trade_list) > 1:
                raise ValidationError(
                    _("交易订单号已存在，正式交易订单的交易订单号不能重复！")
                )

    @api.depends("trade_amount", "reduce_amount")
    def _compute_final_amount(self):
        for trade in self:
            trade.final_amount = trade.trade_amount - trade.reduce_amount


class GuaranteeAccountsRecvTradeReduceReasons(models.Model):
    _name = "ifs.gar.trade.reduce.reasons"
    _description = "交易订单调整理由"

    code = fields.Char("编号", required=True)
    name = fields.Char("名称", required=True)
