# -*- coding: utf-8 -*-

from ast import Bytes
from datetime import datetime, timedelta

from odoo import _, http, fields
from odoo.http import request
from odoo.http import content_disposition, request
from odoo.exceptions import AccessDenied, UserError
from dateutil.relativedelta import relativedelta
import base64, io
import json
import dateutil

from odoo.addons.ifs_gar_review.controllers.main import OpenApiController


class InclusiveFinancingContract(OpenApiController):

    @http.route(
        "/contract/sign_before",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        csrf=False,
    )
    def get_sign_before_page(self, **kwargs):
        return request.render("ifs_gar_contract.factor_sign_before")

    @http.route()
    def merchant_approve(self, entry_code, approval, approval_info, reject_info):
        result_body = super().merchant_approve(
            entry_code, approval, approval_info, reject_info
        )

        entry_merchant = (
            request.env["ifs.gar.entry.merchant"]
            .sudo()
            .search([("seq_code", "=", entry_code)])
        )
        factor_supplier = request.env["ifs.gar.partner.factor.supplier"].search(
            [
                ("supplier_id", "=", entry_merchant.supplier_id.id),
                ("factor_id", "=", entry_merchant.factor_id.id),
            ],
            limit=1,
        )
        if not factor_supplier.id:
            raise AccessDenied(_("无法找到保理方与供应方关联关系"))

        # 买方账款最高子额度合同
        t18_template = request.env["ifs.contract.template"].retrieve_by_code(
            "T18", entry_merchant.factor_id.id
        )
        t18_contract = request.env["ifs.contract.info"].create(
            {
                "name": t18_template.name,
                "partner_one": "%s,%d" % (entry_merchant._name, entry_merchant.id),
                "partner_two": "%s,%d"
                % (entry_merchant.factor_id._name, entry_merchant.factor_id.id),
                "partner_two_signature": entry_merchant.factor_id.signature,
                "params": json.dumps(
                    {
                        "supplier_name": entry_merchant.supplier_id.name,
                        "product_scope": factor_supplier.product_scope,
                        "approved_quota": entry_merchant.supplier_final_quota,
                        "supplier_sign_date": fields.Date.to_string(
                            factor_supplier.t17_contract_info_id.sign_date
                        ),
                    }
                ),
                "template_id": t18_template.id,
            }
        )

        # t18a_template = request.env["ifs.contract.template"].retrieve_by_code(
        #     "T18A", entry_merchant.factor_id.id
        # )
        # t18a_contract = request.env["ifs.contract.info"].create(
        #     {
        #         "name": t18a_template.name,
        #         "partner_one": "%s,%d" % (entry_merchant._name, entry_merchant.id),
        #         "template_id": t18a_template.id,
        #     }
        # )

        # 最高额不可撤销担保书
        t22_template = request.env["ifs.contract.template"].retrieve_by_code(
            "T22", entry_merchant.factor_id.id
        )
        t22_contract = request.env["ifs.contract.info"].create(
            {
                "name": t22_template.name,
                "partner_one": "%s,%d"
                % (
                    entry_merchant.root_employee_id.sudo().user_id._name,
                    entry_merchant.root_employee_id.sudo().user_id.id,
                ),
                "params": json.dumps(
                    {
                        "factor_name": entry_merchant.factor_id.name,
                        "mer_account_compensation_limit": entry_merchant.supplier_final_quota or 0,
                        "ceiling": entry_merchant.supplier_final_quota or 0,
                        "name": entry_merchant.name,
                        "user_name": (
                            entry_merchant.legal_name
                            if entry_merchant.is_self_guarantee
                            else entry_merchant.guarantor_name
                        ),
                        "mobile": (
                            entry_merchant.legal_info.get("phone")
                            if entry_merchant.is_self_guarantee
                            else entry_merchant.guarantor_info.get("guarantor_phone")
                        ),
                        "card_no": (
                            entry_merchant.legal_id_number
                            if entry_merchant.is_self_guarantee
                            else entry_merchant.guarantor_idcard_no
                        ),
                        "sign_partner": 1,
                    }
                ),
                "template_id": t22_template.id,
            }
        )

        entry_merchant.write(
            {
                "t18_contract_info_id": t18_contract.id,
                # "t18a_contract_info_id": t18a_contract.id,
                "t22_contract_info_id": t22_contract.id,
            }
        )

        # contract_info_ids = [t18_contract.id, t18a_contract.id, t22_contract.id]
        contract_info_ids = [t18_contract.id, t22_contract.id]
        entry_approval = (
            request.env["ifs.gar.entry.merchant.approval.info.wizard"]
            .sudo()
            .create(
                {
                    "entry_id": entry_merchant.id,
                    "t18_contract_info_id": t18_contract.id,
                    # "t18a_contract_info_id": t18a_contract.id,
                    "t22_contract_info_id": t22_contract.id,
                }
            )
        )
        sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
            contract_info_ids,
            website_id=request.env.ref("website.default_website").id,
            sign_partner=entry_merchant,
            next_state="signed",
            ref_object=entry_approval,
        )

        message_body = {
            "approval_info": {
                "entry_code": entry_merchant.seq_code,
                "state": "approval",
                "sign_url": sign_token.sign_url,
                "empty_list": [],
                "account_info": {
                    "approved_quota": int(entry_merchant.supplier_final_quota),
                    "credit_term": entry_merchant.credit_term,
                    "repay_day": entry_merchant.repay_day,
                    "financer_code": "",
                    "financer_name": "",
                },
            }
        }
        entry_merchant.message_handler(message_body)

        result_body.update(
            {
                "sign_url": sign_token.sign_url,
            }
        )
        return result_body

    def entry_merchant_state(self, entry_code):
        result_body = super().entry_merchant_state(entry_code)

        entry_merchant = (
            request.env["ifs.gar.entry.merchant"]
            .sudo()
            .search([("seq_code", "=", entry_code)])
        )

        is_sign = True
        if (
            not (not entry_merchant.company_registry and entry_merchant.practice_code)
            and not entry_merchant.trade_license
        ):
            is_sign = False
        if not (entry_merchant.legal_id_number or entry_merchant.guarantor_idcard_no):
            is_sign = False

        if entry_merchant.state == "signed":
            result_body["merchant_code"] = entry_merchant.merchant_id.seq_code
        elif entry_merchant.state == "draft" and is_sign:
            contract_ids = [
                entry_merchant.f41_contract_info_id.id,
                entry_merchant.f42_contract_info_id.id,
                entry_merchant.f43_contract_info_id.id,
            ]
            sign_token = (
                request.env["ifs.contract.info.sign.token"]
                .sudo()
                .search(
                    [
                        (
                            "sign_partner",
                            "=",
                            f"ifs.gar.entry.merchant,{entry_merchant.id}",
                        ),
                        ("contract_info_ids", "in", contract_ids),
                    ]
                )
            )
            if (
                not sign_token.exists()
                or sign_token.expiration <= fields.Datetime.now()
            ):
                sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
                    contract_ids,
                    website_id=request.env.ref("website.default_website").id,
                    sign_partner=entry_merchant,
                    next_state="signed",
                    ref_object=entry_merchant,
                )
            result_body["sign_url"] = sign_token.sign_url
        elif entry_merchant.state == "approval":
            if (
                not entry_merchant.t18_contract_info_id
                or not entry_merchant.t22_contract_info_id
            ):
                raise UserError("未找到对应合同")
            contract_ids = [
                entry_merchant.t18_contract_info_id.id,
                entry_merchant.t22_contract_info_id.id,
            ]
            sign_token = (
                request.env["ifs.contract.info.sign.token"]
                .sudo()
                .search(
                    [
                        (
                            "sign_partner",
                            "=",
                            f"ifs.gar.entry.merchant,{entry_merchant.id}",
                        ),
                        ("contract_info_ids", "in", contract_ids),
                    ]
                )
            )
            entry_approval = (
                request.env["ifs.gar.entry.merchant.approval.info.wizard"]
                .sudo()
                .create(
                    {
                        "entry_id": entry_merchant.id,
                        "t18_contract_info_id": entry_merchant.t18_contract_info_id.id,
                        "t22_contract_info_id": entry_merchant.t22_contract_info_id.id,
                    }
                )
            )
            if (
                not sign_token.exists()
                or sign_token.expiration <= fields.Datetime.now()
            ):
                sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
                    contract_ids,
                    website_id=request.env.ref("website.default_website").id,
                    sign_partner=entry_merchant,
                    next_state="signed",
                    ref_object=entry_approval,
                )
            result_body["sign_url"] = sign_token.sign_url
        if entry_merchant.state in ["approval", "signed"]:
            result_body["account_info"] = {
                "approved_quota": int(entry_merchant.supplier_final_quota),
                "credit_term": entry_merchant.credit_term,
                "repay_day": entry_merchant.repay_day,
                "financer_code": "",
                "financer_name": "",
            }
        return result_body

    @http.route("/contract/download_test", type="http", methods=["GET"], auth="user")
    def download_test(self, **kwargs):
        # invite_franchisee = request.env['ifs.gar.invite.franchisee'].browse(1)
        # factor = request.env['ifs.partner.factor'].browse(1)
        # merchant=request.env['ifs.partner.merchant'].browse(11)
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "D09")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                # 'partner_one': '%s,%d' % ('ifs.partner.merchant', 11),
                # 'partner_one_signature': factor.signature,
                # 'partner_two': '%s,%d' % ('ifs.partner.factor', 1),
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "partner_one_name": "江西友电数字技术有限公司",
                        "partner_two_name": "深圳市云腾智慧科技有限公司",
                        "t20_contract_date": "2023年2月13日",
                        "t20_contract_code": "T20202303007",
                        "accounts": "103,820.00",
                    }
                ),
                "create_date": datetime(2022, 12, 31),
                "sign_date": datetime.now(),
                # 'write_date':datetime(2022,12,31)
            }
        )
        contract_info._contract_sign()
        # signed_file = contract_info._contract_sign()
        # if signed_file:
        #     contract_info.state = 'signed'
        #     contract_info.contract = base64.b64encode(
        #                 signed_file.getvalue())
        # else:
        #     contract_info.state = 'err'

        # reporthttpheaders = [
        #     ('Content-Type', 'application/pdf'),
        #     ('Content-Length', len(signed_file.getvalue())),
        # ]
        # reporthttpheaders.append(
        #     ('Content-Disposition', content_disposition('%s.pdf' % template_id.name)))
        # return request.make_response(signed_file, headers=reporthttpheaders)

    @http.route("/contract/rander_test", type="http", methods=["GET"], auth="user")
    def rander_test(self, **kwargs):
        factor = request.env["ifs.partner.factor"].sudo().browse(1)
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T18A")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 1),
                'partner_one_signature': factor.signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "before_adjust_approved_quota": 9999999,
                        "after_adjust_approved_quota": 8888888,
                        "adjust_reason": "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊",
                        "adjust_basis": "6666666666662嗷嗷嗷啊",
                        "apply_date": "2023年4月26日",
                    }
                ),
            }
        )

        signed_file = contract_info._contract_sign()
        if signed_file:
            contract_info.state = "signed"
            contract_info.contract = base64.b64encode(signed_file.getvalue())
        else:
            contract_info.state = "err"

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(signed_file.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(signed_file, headers=reporthttpheaders)

    @http.route("/contract/rander_test_c10", type="http", methods=["GET"], auth="user")
    def rander_test_c10(self, **kwargs):
        factor = request.env["ifs.partner.factor"].sudo().browse(1)
        bill = request.env["ifs.gar.loan.account.bill"].sudo().browse(1)
        c10_template = request.env["ifs.contract.template"].sudo().retrieve_by_code(
            "C10", factor.id
        )
        start_bill_date_local = fields.Datetime.context_timestamp(
            bill, bill.start_bill_date
        )
        bill_date_local = fields.Datetime.context_timestamp(
            bill, bill.bill_date
        )
        end_bill_date_local = bill_date_local - timedelta(days=1)
        repayment_date_local = fields.Datetime.context_timestamp(
            bill, bill.repayment_date
        ) - timedelta(days=1)
        params = json.dumps(
            {
                "t20_contract_code": str(bill.t20_contract_info_id.code),
                "bill_code": str(bill.code),
                "bill_amount": str(bill.bill_amount),
                "bill_cycle": f'{start_bill_date_local.strftime("%Y年%m月%d日")} - {end_bill_date_local.strftime("%Y年%m月%d日")}',
                "bill_day": bill_date_local.strftime("%Y年%m月%d日"),
                "repayment_day": repayment_date_local.strftime("%Y年%m月%d日"),
            }
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": c10_template.name,
                "partner_one": "%s,%d"
                % (bill.merchant_id._name, bill.merchant_id.id),
                "partner_two": "%s,%d"
                % (bill.factor_id._name, bill.factor_id.id),
                "template_id": c10_template.id,
                "params": params,
                #"partner_one_signature": bill.merchant_id.signature,
                "partner_two_signature": bill.factor_id.signature,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])
        if contract_pdf:
            # signed_file = contract_info._contract_sign()
            # if signed_file:
            contract_info.state = "signed"
            contract_info.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            contract_info.state = "err"

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % c10_template.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_c11", type="http", methods=["GET"], auth="user")
    def rander_test_c11(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "C11")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 5),
                # 'partner_one_signature': factor.signature,
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "template_id": template_id.id,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_c12", type="http", methods=["GET"], auth="user")
    def rander_test_c12(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "C12")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "template_id": template_id.id,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_c13", type="http", methods=["GET"], auth="user")
    def rander_test_c13(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "C13")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "template_id": template_id.id,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_c14", type="http", methods=["GET"], auth="user")
    def rander_test_c14(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "C14")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "template_id": template_id.id,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_d08", type="http", methods=["GET"], auth="user")
    def rander_test_d08(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "D08")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "accounts": "31251341",
                        "t20_contract_date": "2023年4月26日",
                        "t20_contract_code": "T2023261434812",
                    }
                ),
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_f41", type="http", methods=["GET"], auth="user")
    def rander_test_f41(self, **kwargs):
        # legal_id = request.env['ifs.partner.factor'].browse(4).root_employee_id.idcard_id.idcard_no
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "F41")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                # 'partner_two': '%s,%d' % ('ifs.partner.factor', 4),
                "template_id": template_id.id,
            }
        )

        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_f42", type="http", methods=["GET"], auth="user")
    def rander_test_f42(self, **kwargs):

        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "F42")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                # 'partner_two': '%s,%d' % ('ifs.partner.factor', 5),
                "template_id": template_id.id,
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_f43", type="http", methods=["GET"], auth="user")
    def rander_test_f43(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "F43")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                # 'partner_two': '%s,%d' % ('ifs.partner.factor', 5),
                "template_id": template_id.id,
            }
        )
        # contract_info = request.env['ifs.contract.info'].browse(149)
        # template_content = contract_info.generate_contract(contract_info.id)
        # contract_info.write({
        #     'report_content':template_content.get('template_content')
        # })
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_p01", type="http", methods=["GET"], auth="user")
    def rander_test_p01(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "P01")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_two": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(5)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "province": "31251341",
                        "city": "2023年4月26日",
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_p02", type="http", methods=["GET"], auth="user")
    def rander_test_p02(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "P02")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                # 'partner_two': '%s,%d' % ('ifs.partner.factor', 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                # 'partner_two_signature': request.env['ifs.partner.factor'].browse(5).signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "province": "31251341",
                        "city": "2023年4月26日",
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_t17", type="http", methods=["GET"], auth="user")
    def rander_test_t17(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T17")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 1),
                "partner_two": "%s,%d" % ("ifs.partner.supplier", 1),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "product_scope": "AAAAAAAAAAA",
                        "contract_total_quota": 222222,
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        if contract_pdf:
            signed_file = contract_info._contract_sign()
            if signed_file:
                contract_info.state = "signed"
                contract_info.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            contract_info.state = "err"

        # reporthttpheaders = [
        #     ('Content-Type', 'application/pdf'),
        #     ('Content-Length', len(contract_pdf.getvalue())),
        # ]
        # reporthttpheaders.append(
        #     ('Content-Disposition', content_disposition('%s.pdf' % template_id.name)))
        # return request.make_response(contract_pdf, headers=reporthttpheaders)

        # html = report.with_context(context)._render_qweb_html(
        #     report.report_name, contract_info.id, data=data)[0]
        # return request.make_response(html)

    @http.route("/contract/rander_test_t18", type="http", methods=["GET"], auth="user")
    def rander_test_t18(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T18")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 1),
                "partner_two": "%s,%d" % ("ifs.partner.supplier", 1),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "supplier_name": "拼多多",
                        "product_scope": "AAAAAAAAAAA",
                        "approved_quota": 99999,
                        "supplier_sign_date": "313123213",
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        if contract_pdf:
            signed_file = contract_info._contract_sign()
            if signed_file:
                contract_info.state = "signed"
                contract_info.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            contract_info.state = "err"

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_t19", type="http", methods=["GET"], auth="user")
    def rander_test_t19(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T19")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_two": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_three": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(5)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "t17_contract_code": "T17201032139213",
                        "order_code": "ABCDEFG",
                        "trade_amount": 99999,
                        "repayment_date": "2023年7月1日",
                        "product_scope": "ABCABC",
                        "available_quota": 3213218,
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_t20", type="http", methods=["GET"], auth="user")
    def rander_test_t20(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T20")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_two": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_three": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(5)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "t17_contract_code": "T17201032139213",
                        "order_code": "ABCDEFG",
                        "trade_amount": 99999,
                        "repayment_date": "2023年7月1日",
                        "product_scope": "ABCABC",
                        "available_quota": 3213218,
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_t21", type="http", methods=["GET"], auth="user")
    def rander_test_t21(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T21")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 1),
                "partner_two": "%s,%d" % ("ifs.partner.supplier", 1),
                # 'partner_three': '%s,%d' % ('ifs.partner.factor', 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "t17_contract_code": request.env["ifs.contract.info"]
                        .browse(3)
                        .code
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        if contract_pdf:
            signed_file = contract_info._contract_sign()
            if signed_file:
                contract_info.state = "signed"
                contract_info.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            contract_info.state = "err"

        # reporthttpheaders = [
        #     ('Content-Type', 'application/pdf'),
        #     ('Content-Length', len(contract_pdf.getvalue())),
        # ]
        # reporthttpheaders.append(
        #     ('Content-Disposition', content_disposition('%s.pdf' % template_id.name)))
        # return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_t22", type="http", methods=["GET"], auth="user")
    def rander_test_t22(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "T22")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.gar.entry.merchant", 2),
                "partner_two": "%s,%d" % ("ifs.gar.entry.merchant", 2),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "mer_account_compensation_limit": "99999",
                        "ceiling": "99999",  # 最高限额
                        "sign_partner": 2,
                        "name": request.env["ifs.gar.entry.merchant"]
                        .browse(2)
                        .guarantor_name,
                        "mobile": request.env["ifs.gar.entry.merchant"]
                        .browse(2)
                        .guarantor_info.get("guarantor_phone"),
                        "card_no": request.env["ifs.gar.entry.merchant"]
                        .browse(2)
                        .guarantor_idcard_no,
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        if contract_pdf:
            signed_file = contract_info._contract_sign()
            if signed_file:
                contract_info.state = "signed"
                contract_info.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            contract_info.state = "err"

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_x10", type="http", methods=["GET"], auth="user")
    def rander_test_x10(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "X10")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_two": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(5)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "before_adjust_approved_quota": 9999999,
                        "after_adjust_approved_quota": 8888888,
                        "adjust_reason": "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊",
                        "adjust_basis": "6666666666662嗷嗷嗷啊",
                        "apply_date": "2023年4月26日",
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/rander_test_x11", type="http", methods=["GET"], auth="user")
    def rander_test_x10(self, **kwargs):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "X11")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "partner_one": "%s,%d" % ("ifs.partner.factor", 1),
                "partner_two": "%s,%d" % ("ifs.partner.factor", 4),
                "partner_three": "%s,%d" % ("ifs.partner.factor", 5),
                "partner_one_signature": request.env["ifs.partner.factor"]
                .browse(1)
                .signature,
                "partner_two_signature": request.env["ifs.partner.factor"]
                .browse(4)
                .signature,
                "partner_three_signature": request.env["ifs.partner.factor"]
                .browse(5)
                .signature,
                "template_id": template_id.id,
                "params": json.dumps(
                    {
                        "origin_quota": "1111",
                        "apply_quota": "1111",
                    }
                ),
            }
        )
        report = request.env["ir.actions.report"]._get_report_from_name(
            "ifs_contract.print_contract"
        )
        context = dict(request.env.context)
        data = {"context": context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, contract_info.id, data=data
        )

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = "".join([contract_info.name, contract_info.code, ".pdf"])

        reporthttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(contract_pdf.getvalue())),
        ]
        reporthttpheaders.append(
            ("Content-Disposition", content_disposition("%s.pdf" % template_id.name))
        )
        return request.make_response(contract_pdf, headers=reporthttpheaders)

    @http.route("/contract/z10/credit_sign", type="http", methods=["GET"], auth="user")
    def credit_sign_z10(self):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "Z10")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "template_id": template_id.id,
                "partner_one_signature": request.env["ifs.contract.info"]
                .sudo()
                .browse(1)
                .partner_one_signature,
                "partner_two_signature": request.env["ifs.contract.info"]
                .sudo()
                .browse(1)
                .partner_two_signature,
                "params": json.dumps(
                    {
                        "partner_one_name": "江西友电数字技术有限公司",
                        "partner_two_name": "深圳市云腾智慧科技有限公司",
                        "partner_one_corp_name": "张三",
                        "partner_two_corp_name": "胡明钊",
                        "partner_one_address": "福建省平潭综合实验金井湾海峡如意城帝景苑12号楼3001室",
                        "partner_two_address": "深圳市南山区南头街道大汪山社区南光路286号水木一方大厦1栋1702",
                        "partner_one_phone": "13555555555",
                        "partner_two_phone": "13666666666",
                    }
                ),
                "expire_date": datetime.now() + relativedelta(years=1),
            }
        )

        sign_partner = request.env["ifs.partner.factor"].browse(1)
        sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
            [contract_info.id],
            website_id=request.env.ref("website.default_website").id,
            sign_partner=sign_partner,
            sign_name="张三",
            idcard="440923200001014567",
            next_state="unconfirmed",
        )

        return json.dumps({"sign_url": sign_token.sign_url})

    @http.route(
        "/contract/z10/credit_sign_2", type="http", methods=["GET"], auth="user"
    )
    def credit_sign_z10_2(self):
        contract_info = request.env["ifs.contract.info"].browse(13)

        sign_partner = request.env["ifs.partner.factor"].browse(1)
        sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
            [contract_info.id],
            website_id=request.env.ref("website.default_website").id,
            sign_partner=sign_partner,
            token_type="partner_two",
            sign_name="胡明钊",
            idcard="440923200001014568",
            next_state="signed",
        )

        return json.dumps({"sign_url": sign_token.sign_url})

    @http.route("/contract/z20/credit_sign", type="http", methods=["GET"], auth="user")
    def credit_sign_z20(self):
        template_id = request.env["ifs.contract.template"].search(
            [("code", "=", "Z20")]
        )
        contract_info = request.env["ifs.contract.info"].create(
            {
                "name": template_id.name,
                "template_id": template_id.id,
                "partner_one_signature": request.env["ifs.contract.info"]
                .sudo()
                .browse(1)
                .partner_one_signature,
                "partner_two_signature": request.env["ifs.contract.info"]
                .sudo()
                .browse(1)
                .partner_two_signature,
                "params": json.dumps(
                    {
                        "partner_one_name": "江西友电数字技术有限公司",
                        "partner_two_name": "深圳市云腾智慧科技有限公司",
                        "partner_one_corp_name": "张三",
                        "partner_two_corp_name": "胡明钊",
                        "partner_one_address": "福建省平潭综合实验金井湾海峡如意城帝景苑12号楼3001室",
                        "partner_two_address": "深圳市南山区南头街道大汪山社区南光路286号水木一方大厦1栋1702",
                        "partner_one_phone": "13555555555",
                        "partner_two_phone": "13666666666",
                        "account_name": "云腾智慧",
                        "bank_no": "651215421515212151521",
                        "bank_name": "中国交通银行",
                    }
                ),
                "expire_date": datetime.now() + relativedelta(years=1),
            }
        )

        sign_partner = request.env["ifs.partner.factor"].browse(1)
        sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
            [contract_info.id],
            website_id=request.env.ref("website.default_website").id,
            sign_partner=sign_partner,
            sign_name="张三",
            idcard="440923200001014567",
            next_state="unconfirmed",
        )

        return json.dumps({"sign_url": sign_token.sign_url})

    @http.route(
        "/contract/z20/credit_sign_2", type="http", methods=["GET"], auth="user"
    )
    def credit_sign_z20_2(self):
        contract_info = request.env["ifs.contract.info"].browse(17)

        sign_partner = request.env["ifs.partner.factor"].browse(1)
        sign_token = request.env["ifs.contract.info.sign.token"].prepare_sign(
            [contract_info.id],
            website_id=request.env.ref("website.default_website").id,
            sign_partner=sign_partner,
            token_type="partner_two",
            sign_name="胡明钊",
            idcard="440923200001014568",
            next_state="signed",
        )

        return json.dumps({"sign_url": sign_token.sign_url})

    @http.route("/contract/sign/<int:id>", type="http", methods=["GET"], auth="user")
    def manual_sign(self, id):
        request.env["ifs.contract.info"].browse(id).signature_all()

        return "ok"


    @http.route("/contract/sign_test/<string:template_code>", type="http", methods=["GET"], auth="user")
    def sign_test(self, template_code):
        factor_id = request.env['ifs.partner.factor'].search([('seq_code', '=', '9000001')])
        supplier_id = request.env['ifs.partner.supplier'].search([('seq_code', '=', '3000001')])

        entry_supplier_id = request.env['ifs.gar.entry.supplier'].search([('seq_code', '=', 'SE20251225100535006')])
        entry_merchant_id = request.env['ifs.gar.entry.merchant'].search([('seq_code', '=', 'ME20251225145802003')])

        if template_code == "F41":
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'F41', factor_id.id, supplier_id.id)
            f41_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                'template_id': template.id,
                'partner_one': '%s,%d' % (entry_supplier_id._name, entry_supplier_id.id),
                'partner_one_signature': supplier_id.signature,
                'params': json.dumps({
                    'name': entry_supplier_id.legal_name,
                    'id_number': entry_supplier_id.legal_id_number,
                }),
            })
            
            f41_contract.signature_all()
        elif template_code == "F42":
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'F42', factor_id.id, supplier_id.id)
            f42_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                'template_id': template.id,
                'partner_one': '%s,%d' % (entry_supplier_id._name, entry_supplier_id.id),
                'partner_one_signature': supplier_id.signature,
            })
            
            f42_contract.signature_all()
        elif template_code == "F43":
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'F43', factor_id.id, supplier_id.id)
            f43_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                'template_id': template.id,
                'partner_one': '%s,%d' % (entry_supplier_id._name, entry_supplier_id.id),
                'partner_one_signature': supplier_id.signature,
            })
            
            f43_contract.signature_all()
        elif template_code == 'T17':
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'T17', factor_id.id, supplier_id.id)
            t17_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                'partner_one': '%s,%d' % (supplier_id._name, supplier_id.id),
                'partner_two': '%s,%d' % (factor_id._name, factor_id.id),
                'partner_one_signature': supplier_id.signature,
                'partner_two_signature': factor_id.signature,
                'template_id': template.id,
                'params': json.dumps({
                    'product_scope': '药品',
                    'contract_total_quota': 1_000_000_000/10000,
                    'fee_solution_contract_content': '',
                }),
            })
            t17_contract.signature_all()
        elif template_code == 'T19B':
            bill = request.env['ifs.gar.loan.account.bill'].browse(16)
            start_bill_date_local = fields.Datetime.context_timestamp(
                bill, bill.start_bill_date
            )
            bill_date_local = fields.Datetime.context_timestamp(
                bill, bill.bill_date
            )
            end_bill_date_local = bill_date_local - timedelta(days=1)
            repayment_date_local = fields.Datetime.context_timestamp(
                bill, bill.repayment_date
            ) - timedelta(days=1)
            params = json.dumps({
                "t17_contract_code": "T17202602015",
                "bill_code": str(bill.code),
                "bill_amount": str(bill.bill_amount),
                "bill_cycle": f'{start_bill_date_local.strftime("%Y年%m月%d日")} - {end_bill_date_local.strftime("%Y年%m月%d日")}',
                "bill_day": bill_date_local.strftime("%Y年%m月%d日"),
                "repayment_day": repayment_date_local.strftime(
                    "%Y年%m月%d日"
                ),
                "product_scope": bill.sub_loan_account_id.factor_supplier_id.product_scope,
                "available_quota": bill.sub_loan_account_id.available_quota,
            })
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'T19B', factor_id.id, supplier_id.id)
            t19b_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                "partner_one": "%s,%d"
                    % (bill.factor_id._name, bill.factor_id.id),
                    "partner_two": "%s,%d"
                    % (bill.supplier_id._name, bill.supplier_id.id),
                    "partner_three": "%s,%d"
                    % (bill.merchant_id._name, bill.merchant_id.id),
                    "template_id": template.id,
                    "params": params,
                    "partner_two_signature": bill.supplier_id.signature,
            })
            t19b_contract.signature_all()
        elif template_code == 'T18':
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'T18', factor_id.id, supplier_id.id)
            t18_contract = request.env['ifs.contract.info'].create({
                'name': template.name,
                'template_id': template.id,
                'partner_one': '%s,%d' % (entry_merchant_id._name, entry_merchant_id.id),
                'partner_one_signature': supplier_id.signature,
                'partner_two': '%s,%d' % (factor_id._name, factor_id.id),
                'partner_two_signature': factor_id.signature,
                'params': json.dumps({
                    'supplier_name': supplier_id.name,
                    'product_scope': '药品',
                    'approved_quota': 3000,
                    'supplier_sign_date': "2025-12-25",
                }),
            })
            t18_contract.signature_all()
        elif template_code == 'T18A':
            template = request.env["ifs.contract.template"].retrieve_by_code(
                "T18A", factor_id.id
            )
            t18a_contract = request.env["ifs.contract.info"].create(
                {
                    "name": template.name,
                    "partner_one": "%s,%d" % (entry_merchant_id._name, entry_merchant_id.id),
                    "partner_one_signature": supplier_id.signature,
                    "template_id": template.id,
                }
            )
            t18a_contract.signature_all()
        elif template_code == 'T22':
            template = request.env['ifs.contract.template'].retrieve_by_code(
                'T22', factor_id.id, supplier_id.id)
            t22_contract = request.env["ifs.contract.info"].create({
                "name": template.name,
                "partner_one": "%s,%d"
                % (
                    entry_merchant_id.root_employee_id.sudo().user_id._name,
                    entry_merchant_id.root_employee_id.sudo().user_id.id,
                ),
                "params": json.dumps(
                    {
                        "factor_name": entry_merchant_id.factor_id.name,
                        "mer_account_compensation_limit": entry_merchant_id.supplier_final_quota or 0,
                        "ceiling": entry_merchant_id.supplier_final_quota or 0,
                        "name": entry_merchant_id.name,
                        "user_name": (
                            entry_merchant_id.legal_name
                            if entry_merchant_id.is_self_guarantee
                            else entry_merchant_id.guarantor_name
                        ),
                        "mobile": (
                            entry_merchant_id.legal_info.get("phone")
                            if entry_merchant_id.is_self_guarantee
                            else entry_merchant_id.guarantor_info.get("guarantor_phone")
                        ),
                        "card_no": (
                            entry_merchant_id.legal_id_number
                            if entry_merchant_id.is_self_guarantee
                            else entry_merchant_id.guarantor_idcard_no
                        ),
                        "sign_partner": 1,
                    }
                ),
                "template_id": template.id,
            })
            t22_contract.signature_all()
