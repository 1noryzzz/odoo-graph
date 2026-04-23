# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InclusiveFinancingRepaymentOrder(models.Model):
    _name = "ifs.gar.repayment.order"
    _description = "还款单"
    _inherit = ["ifs.ir.sequence.mixin"]
    _order = "id desc"

    bill_code = fields.Char("账单编号", required=True)
    bill_id = fields.Many2one(
        "ifs.gar.loan.account.bill",
        string="账单",
        required=True,
        ondelete="restrict",
        index=True,
    )
    sub_loan_account_id = fields.Many2one(
        "ifs.gar.sub.loan.account",
        string="子账户",
        related="bill_id.sub_loan_account_id",
    )
    merchant_code = fields.Char("采购方编号", required=True)
    operate_type = fields.Selection([
        ('refund', '退款'),
        ('repayment', '还款'),
        ('fuse', '熔断')
    ], string='操作类型', required=True, readonly=True)
    repay_amount = fields.Monetary("还款金额", required=True)
    currency_id = fields.Many2one(
        "res.currency", string="币种", required=True, related="bill_id.currency_id"
    )

    factor_id = fields.Many2one(
        "ifs.partner.factor",
        related="bill_id.factor_id",
        string="保理方",
        readonly=True,
    )
    merchant_id = fields.Many2one(
        "ifs.partner.merchant",
        related="bill_id.merchant_id",
        string="采购方",
        readonly=True,
    )
    supplier_id = fields.Many2one(
        "ifs.partner.supplier",
        related="bill_id.supplier_id",
        string="供应方",
        readonly=True,
    )
    remark = fields.Text("备注")

    @api.model
    def repay_bill(
        self,
        supplier,
        merchant_code,
        bill_code,
        repay_amount,
        operate_type="repayment",
        remark=None,
    ):
        merchant = self.env["ifs.partner.merchant"].search(
            [("seq_code", "=", merchant_code)]
        )
        if not merchant.exists():
            raise UserError(_("采购方编号有误，未找到对应的采购方！"))
        sub_loan_account = (
            self.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [("supplier_id", "=", supplier.id), ("merchant_id", "=", merchant.id)]
            )
        )
        if not sub_loan_account.exists():
            raise UserError(_("该供应方下未找到对应采购方编号的子账户！"))

        bill = self.env["ifs.gar.loan.account.bill"].search(
            [
                ("code", "=", bill_code),
                ("sub_loan_account_id", "=", sub_loan_account.id),
            ]
        )
        if not bill.exists():
            raise UserError(_("账单不存在！"))

        repayment_order = self.create({
            "bill_id": bill.id,
            "bill_code": bill.code,
            "merchant_code": merchant_code,
            "operate_type": operate_type,
            "repay_amount": repay_amount,
            "remark": remark,
        })

        if bill.state in ["current", "pending", "overdue"]:
            bill_log = bill.insert_bill(
                sub_loan_account,
                repayment_order,
                operate_type,
                -repay_amount,
                remark=remark,
                record_bill=bill,
            )
            if bill_log:
                return repayment_order
            else:
                raise UserError(_("还款失败！"))
        elif bill.state in ["paid", "settle"]:
            raise UserError(_("账单已还清！"))
        else:
            raise UserError(_("账单状态不正确！"))
