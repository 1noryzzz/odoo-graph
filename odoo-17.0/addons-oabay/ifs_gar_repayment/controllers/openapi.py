# -*- coding: utf-8 -*-

from . import openapi
import logging
import requests
import base64
from odoo.http import Controller, request, route
from odoo import _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OpenApiController(Controller):

    @route(
        ["/openapi/repayment/do_repay"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def do_repay(
        self,
        merchant_code,
        bill_code,
        repay_amount,
        operate_type="repayment",
        remark=None,
    ):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier:
            raise UserError("没有找到对应的供应商！")
        
        repayment_order = request.env["ifs.gar.repayment.order"].repay_bill(
            supplier, merchant_code, bill_code, repay_amount, operate_type, remark)

        return {
            "merchant_code": repayment_order.merchant_code,
            "repayment_code": repayment_order.seq_code,
            "bill_info": {
                "bill_code": repayment_order.bill_id.code,
                "state": repayment_order.bill_id.state,
                "repayment_date": fields.Datetime.context_timestamp(repayment_order, repayment_order.bill_id.repayment_date),
                "bill_amount": repayment_order.bill_id.bill_amount,
                "interest": repayment_order.bill_id.pending_interest,
                "damages": repayment_order.bill_id.pending_damages,
                "repayment_amount": repayment_order.bill_id.repayment_amount,
                "pending_amount": repayment_order.bill_id.pending_amount,
            }
        }

    @route(
        ["/openapi/repayment/merchant_repay"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def create_order(self, apikey, order_no, payment_receipt_url):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier:
            raise UserError("没有找到对应的供应商！")
        api_app = (
            request.env["galaxy.open.api.app"]
            .sudo()
            .search([("owner_id", "=", f"ifs.partner.supplier,{supplier.id}")], limit=1)
        )
        if not api_app:
            raise UserError(_("没有找到对应的应用Owner！"))
        user_id = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", api_app.app_id, scope="galaxy.open.api", key=apikey
            )
        )
        if not user_id:
            raise UserError(_("没有找到对应的采购方用户！"))
        user = request.env["res.users"].search([("id", "=", user_id)])
        merchant = request.env["ifs.partner.merchant"].search(
            [("company_id", "=", user.company_id.id)]
        )
        if not merchant:
            raise UserError("未找到对应的采购方，只有采购方才能进行还款操作！")
        request.update_env(
            user=user.id,
            context={
                **request.env.context,
                "allowed_company_ids": merchant.company_id.ids,
            },
        )
        if not order_no or not payment_receipt_url:
            raise UserError("参数不能为空！")
        resp_payment_receipt = requests.get(payment_receipt_url)
        if resp_payment_receipt.status_code == 200:
            payment_receipt = base64.b64encode(resp_payment_receipt.content)
        else:
            raise UserError("获取付款凭证文件失败，请检查文件路径是否有误！")
        trade_order = request.env["ifs.gar.trade.order"].search(
            [("seq_code", "=", order_no)]
        )
        if not trade_order:
            raise UserError("未找到对应的交易订单，请检查订单号是否正确！")
        if not trade_order.t19_contract_state in [
            "signed",
            "committed",
        ] or not trade_order.t20_contract_state in ["signed", "committed"]:
            raise UserError("该交易订单签约合同未全部完成签约，无法进行还款操作！")
        if trade_order.plan_ids[0].can_repayment:
            trade_order.plan_ids[0].write(
                {"state": "repaid", "payment_receipt": payment_receipt}
            )
        else:
            raise UserError("该交易订单当前状态不可还款！")

        return {
            "message": "操作成功！",
        }

    @route(
        ["/openapi/repayment/supplier_withdraw"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def supplier_confirm_order(self, order_no, remark):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier:
            raise UserError("只有供应商才能发起提款！")
        if not order_no:
            raise UserError("订单号不能为空！")
        trade_order = request.env["ifs.gar.trade.order"].search(
            [("seq_code", "=", order_no)]
        )
        if not trade_order:
            raise UserError("未找到对应的交易订单，请检查订单号是否正确！")
        if trade_order.plan_ids[0].can_withdraw:
            trade_order.plan_ids[0].write({"remark": remark})
            trade_order.plan_ids[0].action_withdraw()
        else:
            raise UserError("该交易订单当前状态不可提款！")

        return {
            "message": "操作成功！",
        }

    @route(
        ["/openapi/trade/circuit_breaker"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def supplier_trade_fusing(self, order_no, fuse_remark):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier:
            raise UserError("只有供应商才能发起熔断！")
        if not order_no:
            raise UserError("订单号不能为空！")
        order = request.env["ifs.gar.trade.order"].search([("seq_code", "=", order_no)])
        if not order.exists():
            raise UserError("未找到对应的交易订单，请检查订单号是否正确！")
        url = ""
        if order.state != "fuse" and order.can_fuse:
            order.write({"fuse_remark": fuse_remark})
            cb_wizard = request.env[
                "ifs.gar.trade.order.circuit.breaker.wizard"
            ].create(
                {
                    "trade_order_id": order.id,
                }
            )
            res = cb_wizard.action_breaker()
            if res:
                url = res.get("context").get("default_sign_url")
            else:
                raise UserError("熔断操作出现异常，请联系管理人员！")
        else:
            raise UserError("该交易订单当前状态不可熔断！")
        return {
            "message": "操作成功！",
            "url": url,
        }
