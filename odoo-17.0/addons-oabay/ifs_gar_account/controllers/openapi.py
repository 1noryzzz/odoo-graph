# -*- coding: utf-8 -*-

import logging
import io
import random
import string
import pytz

from datetime import timedelta, datetime, time

from odoo.tools.misc import xlsxwriter
from odoo.http import Controller, request, route
from odoo import _, fields
from odoo.exceptions import UserError, ValidationError
from cache_base import retrieve_cache_base
from odoo.http import content_disposition, request

_logger = logging.getLogger(__name__)


class OpenApiController(Controller):

    @route(
        ["/openapi/merchant/account_info"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def merchant_account_info(self, merchant_code):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier.exists():
            raise UserError(_("只有供应方才能获取采购方账户信息！"))
        merchent = request.env["ifs.partner.merchant"].search(
            [("seq_code", "=", merchant_code)]
        )
        if not merchent.exists():
            raise UserError(_("采购方编号有误，未找到对应的采购方！"))
        loan_account = (
            request.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [("supplier_id", "=", supplier.id), ("merchant_id", "=", merchent.id)]
            )
        )
        if not loan_account.exists():
            raise UserError(_("该供应方下未找到对应采购方编号的子账户！"))
        return {
            "state": loan_account.state,
            "approved_quota": loan_account.approved_quota,
            "available_quota": loan_account.available_quota,
            "freeze_quota": loan_account.freeze_quota,
            "used_quota": loan_account.used_quota,
            "bill_date": 1,  # 暂时写死
            "bill_amount": 0,  # 暂时写死
            "pending_amount": loan_account.used_quota,  # 暂时为已用额度
        }

    @route(
        ["/openapi/account/truncate"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def account_truncate(self, merchant_code, reason):
        if not (merchant_code and reason):
            raise UserError(_("参数不能为空！"))
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier.exists():
            raise UserError(_("无权限获取采购方账户信息！"))
        merchant = request.env["ifs.partner.merchant"].search(
            [("seq_code", "=", merchant_code)]
        )
        if not merchant.exists():
            raise UserError(_("采购方编号有误，未找到对应的采购方！"))
        loan_account = (
            request.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [("supplier_id", "=", supplier.id), ("merchant_id", "=", merchant.id)],
                limit=1,
            )
        )
        if not loan_account.exists():
            raise UserError(_("未找到对应采购方编号的账户！"))
        is_uncleared = bool(
            loan_account.filtered(
                lambda loan: any(
                    bill.freeze_quota != 0 or bill.used_quota != 0
                    for bill in loan.bill_ids
                )
            )
        )
        if is_uncleared:
            raise UserError(_("此账户有业务未结清，不可注销"))
        loan_account.write({"state": "freeze", "reason": reason})
        return {"truncated": True}

    @route(
        ["/openapi/bill/retrieve_daliy_bill"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def retrieve_daliy_bill(self, bill_date=None):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )

        if not isinstance(bill_date, str) or bill_date == "":
            current_utc_time = datetime.utcnow()
            yesterday = current_utc_time - timedelta(days=1)
            bill_date = yesterday.strftime("%Y-%m-%d")

        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        token = "".join(random.sample(string.ascii_letters + string.digits, 8))
        with cache_base.redis_db.connection_open() as db:
            db.setex(
                name=f"OPENAPI:retrieve_daliy_bill:{token}",
                value=str(supplier.seq_code),
                time=7200,
            )
        return {"bill_date": bill_date, "token": token}

    @route(
        ["/openapi/bill/pending_credit"], type="http", auth="public", methods=["GET"]
    )
    def pending_credit(self, token, bill_date=None):
        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            value = db.get(f"OPENAPI:retrieve_daliy_bill:{token}")
            if not value:
                raise ValidationError("token不存在或已过期")

        now = datetime.now()
        current_timezone = now.astimezone().tzinfo
        tz_utc8 = pytz.timezone("Asia/Shanghai")
        # 与UTC+8时区的时差
        time_diff = tz_utc8.utcoffset(now) - current_timezone.utcoffset(now)

        date_obj = fields.Date.from_string(bill_date)
        yesterday = (datetime.now() + time_diff - timedelta(days=1)).date()
        if date_obj > yesterday:
            raise ValidationError("对账日期错误！")

        start_date = datetime.combine(date_obj, time.min)
        start_date = start_date - time_diff
        end_date = datetime.combine(date_obj, time.max)
        end_date = end_date - time_diff

        trade_list = (
            request.env["ifs.gar.trade.list"]
            .sudo()
            .search(
                [
                    ("bill_log_id.create_date", ">=", start_date),
                    ("bill_log_id.create_date", "<=", end_date),
                    ("bill_log_id.operate_type", "=", "freeze"),
                ]
            )
        )

        index = 0
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("sheet1")
        title_list = [
            "商城订单号",
            "支付订单号",
            "供应方商编",
            "付款方商编",
            "原始金额（单位分）",
            "交易日期",
            "支付订单生成时间",
            "调减金额",
            "最后修改时间",
        ]
        for x, title in enumerate(title_list):
            worksheet.write(index, x, title)

        for item in trade_list:
            # 支付订单生成时间
            create_date_utc8 = item.payment_id.create_date + time_diff
            # 确认收货时间
            write_date_utc8 = item.write_date + time_diff
            index += 1
            worksheet.write(index, 0, item.trade_code)
            worksheet.write(index, 1, item.payment_id.seq_code)
            worksheet.write(index, 2, item.supplier_code)
            worksheet.write(index, 3, item.payment_id.merchant_code)
            worksheet.write(index, 4, int(item.trade_amount))
            worksheet.write(index, 5, item.trade_date.strftime("%Y-%m-%d"))
            worksheet.write(index, 6, create_date_utc8.strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.write(index, 7, int(item.reduce_amount))
            worksheet.write(index, 8, write_date_utc8.strftime("%Y-%m-%d %H:%M:%S"))

        workbook.close()
        output.seek(0)
        response = request.make_response(
            output.read(),
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", content_disposition("未出账对账单.xlsx")),
            ],
        )

        return response

    @route(
        ["/openapi/bill/already_credit"], type="http", auth="public", methods=["GET"]
    )
    def already_credit(self, token, bill_date=None):
        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            value = db.get(f"OPENAPI:retrieve_daliy_bill:{token}")
            if not value:
                raise ValidationError("token不存在或已过期")

        now = datetime.now()
        current_timezone = now.astimezone().tzinfo
        tz_utc8 = pytz.timezone("Asia/Shanghai")
        # 与UTC+8时区的时差
        time_diff = tz_utc8.utcoffset(now) - current_timezone.utcoffset(now)

        date_obj = fields.Date.from_string(bill_date)
        yesterday = (datetime.now() + time_diff - timedelta(days=1)).date()
        if date_obj > yesterday:
            raise ValidationError("对账日期错误！")

        start_date = datetime.combine(date_obj, time.min)
        start_date = start_date - time_diff
        end_date = datetime.combine(date_obj, time.max)
        end_date = end_date - time_diff
        trade_list = (
            request.env["ifs.gar.trade.list"]
            .sudo()
            .search(
                [
                    ("bill_log_id.create_date", ">=", start_date),
                    ("bill_log_id.create_date", "<=", end_date),
                    ("bill_log_id.operate_type", "=", "loan"),
                ]
            )
        )
        index = 0
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("sheet1")
        title_list = [
            "商城订单号",
            "支付订单号",
            "供应方商编",
            "付款方商编",
            "原始金额（单位分）",
            "交易日期",
            "支付订单生成时间",
            "调减金额",
            "确认收货时间",
        ]
        for x, title in enumerate(title_list):
            worksheet.write(index, x, title)

        for item in trade_list:
            # 支付订单生成时间
            create_date_utc8 = item.payment_id.create_date + time_diff
            # 确认收货时间
            write_date_utc8 = item.write_date + time_diff
            index += 1
            worksheet.write(index, 0, item.trade_code)
            worksheet.write(index, 1, item.payment_id.seq_code)
            worksheet.write(index, 2, item.supplier_code)
            worksheet.write(index, 3, item.payment_id.merchant_code)
            worksheet.write(index, 4, int(item.trade_amount))
            worksheet.write(index, 5, item.trade_date.strftime("%Y-%m-%d"))
            worksheet.write(index, 6, create_date_utc8.strftime("%Y-%m-%d %H:%M:%S"))
            worksheet.write(index, 7, int(item.reduce_amount))
            worksheet.write(index, 8, write_date_utc8.strftime("%Y-%m-%d %H:%M:%S"))

        workbook.close()
        output.seek(0)
        response = request.make_response(
            output.read(),
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", content_disposition("已出账对账单.xlsx")),
            ],
        )

        return response

    @route(
        ["/openapi/account/account_info"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def account_info(self, merchant_code=None, entry_code=None):
        if not merchant_code and not entry_code:
            raise ValidationError("参数为空")

        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier.exists():
            raise UserError(_("无权限！"))

        if merchant_code:
            merchant = (
                request.env["ifs.partner.merchant"]
                .sudo()
                .search([("seq_code", "=", merchant_code)])
            )
            if not merchant.exists():
                raise ValidationError("未找到对应采购方！")
        else:
            entry_merchant = (
                request.env["ifs.gar.entry.merchant"]
                .sudo()
                .search(
                    [("seq_code", "=", entry_code)], order="create_date DESC", limit=1
                )
            )
            if not entry_merchant.exists():
                raise ValidationError("未找到对应进件信息！")
            if not entry_merchant.merchant_id:
                raise ValidationError("进件信息未通过！")
            merchant = entry_merchant.merchant_id

        loan_account = (
            request.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [("supplier_id", "=", supplier.id), ("merchant_id", "=", merchant.id)]
            )
        )
        if not loan_account.exists():
            raise UserError(_("未找到对应采购方的子账户！"))

        now = datetime.now()
        bill_ids = loan_account.bill_ids
        bill_amount = sum(
            [
                bill_id.bill_amount
                for bill_id in bill_ids
                if bill_id.state in ["current", "pending", "overdue"]
            ]
        )
        pending_amount = sum(
            [bill_id.used_quota for bill_id in bill_ids if bill_id.state == "current"]
        )

        if loan_account.state != "overdue":
            bill_ids = filter(lambda bill_id: bill_id.repayment_date > now, bill_ids)
            bill_ids = sorted(bill_ids, key=lambda bill_id: bill_id.repayment_date)
            if len(bill_ids) > 0:
                recently_repayment_date = fields.Datetime.context_timestamp(
                    request.env.company, bill_ids[0].repayment_date
                )
                recently_bill_amount = bill_ids[0].bill_amount
                repayment_amount = recently_bill_amount - bill_ids[0].repayment_amount
            else:
                recently_repayment_date = None
                recently_bill_amount = 0
                repayment_amount = 0
        else:
            bill_ids = filter(lambda bill_id: bill_id.state == "overdue", bill_ids)
            bill_ids = sorted(bill_ids, key=lambda bill_id: bill_id.repayment_date)
            recently_repayment_date = fields.Datetime.context_timestamp(
                request.env.company, bill_ids[0].repayment_date
            )
            recently_bill_amount = bill_ids[0].bill_amount
            repayment_amount = sum(
                [
                    bill_id.pending_amount
                    # + bill_id.pending_interest
                    # + bill_id.pending_damages
                    # - bill_id.repayment_amount
                    for bill_id in bill_ids
                ]
            )

        return {
            "state": loan_account.state,
            "approved_quota": loan_account.approved_quota,
            "available_quota": loan_account.available_quota,
            "freeze_quota": loan_account.freeze_quota,
            "used_quota": loan_account.used_quota,
            "bill_day": 1,
            "bill_amount": bill_amount,
            "pending_amount": pending_amount,
            "credit_term": loan_account.credit_term,
            "repay_day": loan_account.repay_day,
            "financer_code": "",
            "financer_name": "",
            "recently_repayment_date": recently_repayment_date,
            "recently_bill_amount": recently_bill_amount,
            "recently_waiting_amount": repayment_amount,  # 逾期账单金额 + 逾期利息 - 已还
        }

    @route(
        ["/openapi/account/bill_info"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def bill_info(self, merchant_code, bill_code=None):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier.exists():
            raise UserError(_("无权限！"))

        merchant = (
            request.env["ifs.partner.merchant"]
            .sudo()
            .search([("seq_code", "=", merchant_code)])
        )

        loan_account = (
            request.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [("supplier_id", "=", supplier.id), ("merchant_id", "=", merchant.id)]
            )
        )
        if not loan_account.exists():
            raise UserError(_("未找到对应采购方的子账户！"))

        bill_domain = [('sub_loan_account_id', '=', loan_account.id)]
        if bill_code:
            bill_domain.append(('code', '=', bill_code))
        else:
            bill_domain.append(('state', 'in', ['pending', 'overdue']))


        pending_bill = request.env['ifs.gar.loan.account.bill'].sudo().search(bill_domain, limit=1)
        trade_list = request.env['ifs.gar.trade.list'].sudo().search([('bill_id','=', pending_bill.id)])
        return {
            'merchant_code': pending_bill.merchant_id.seq_code,
            'bill_code': pending_bill.code,
            'state': pending_bill.state,
            'start_bill_date': fields.Datetime.context_timestamp(pending_bill, pending_bill.start_bill_date).strftime("%Y-%m-%d"),
            'bill_date': fields.Datetime.context_timestamp(pending_bill, pending_bill.bill_date).strftime("%Y-%m-%d"),
            'repayment_date': fields.Datetime.context_timestamp(pending_bill, pending_bill.repayment_date).strftime("%Y-%m-%d"),
            'bill_amount': pending_bill.bill_amount if pending_bill.bill_amount != 0 else 0,
            'damages': pending_bill.pending_damages if pending_bill.pending_damages != 0 else 0,
            'interest': pending_bill.pending_interest if pending_bill.pending_interest != 0 else 0,
            'repayment_amount': pending_bill.repayment_amount if pending_bill.repayment_amount != 0 else 0,
            'pending_amount': pending_bill.pending_amount if pending_bill.pending_amount != 0 else 0,
            'fee': pending_bill.fee if pending_bill.fee != 0 else 0,
            'trade_list':[{
                'supplier_code':trade_list_id.supplier_code,
                'trade_code':trade_list_id.trade_code,
                'trade_amount': (trade_list_id.trade_amount - trade_list_id.reduce_amount),
                'trade_date': trade_list_id.trade_date.strftime("%Y-%m-%d"),
                'remark':''
            }for trade_list_id in trade_list],
            # 'repayment_list':[]
        }

    @route(
        ["/openapi/bill/change_bill_info"],
        type="json",
        auth="openapi",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def change_bill_info(self, merchant_code, repay_day, credit_term):
        supplier = request.env["ifs.partner.supplier"].search(
            [("company_id", "=", request.env.company.id)]
        )
        if not supplier.exists():
            raise UserError(_("无权限！"))

        sub_loan_account = (
            request.env["ifs.gar.sub.loan.account"]
            .sudo()
            .search(
                [
                    ("supplier_id", "=", supplier.id),
                    ("merchant_id.seq_code", "=", merchant_code),
                ]
            )
        )
        if not sub_loan_account.exists():
            raise UserError(_("未找到对应采购方的子账户！"))

        sub_loan_account.loan_account_id.write(
            {"repay_day": repay_day, "credit_term": credit_term}
        )

        return {
            "merchant_code": merchant_code,
            "account_info": {
                "approved_quota": sub_loan_account.approved_quota,
                "credit_term": sub_loan_account.loan_account_id.credit_term,
                "repay_day": sub_loan_account.loan_account_id.repay_day,
            },
        }
