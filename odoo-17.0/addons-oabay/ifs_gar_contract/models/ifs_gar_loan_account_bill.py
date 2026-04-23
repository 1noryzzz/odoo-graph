# -*- coding: utf-8 -*-

import json
from datetime import timedelta

from odoo import models, fields


class InclusiveFinancingLoanAccountBill(models.Model):
    _inherit = "ifs.gar.loan.account.bill"

    d08_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应收账款结清证明"
    )
    d08_contract_name = fields.Char(
        "应收账款结清证明", related="d08_contract_info_id.name"
    )
    d08_contract_pdf = fields.Binary(
        "应收账款结清证明", related="d08_contract_info_id.contract"
    )
    d08_contract_state = fields.Selection(
        "应收账款结清证明状态", related="d08_contract_info_id.state"
    )
    d08_contract_preview = fields.Binary(
        "应收账款结清证明图片", related="d08_contract_info_id.contract_preview"
    )

    t19_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应收账款转让确认书"
    )
    t19_contract_name = fields.Char(
        "应收账款转让确认书", related="t19_contract_info_id.name"
    )
    t19_contract_pdf = fields.Binary(
        "应收账款转让确认书", related="t19_contract_info_id.contract"
    )
    t19_contract_state = fields.Selection(
        "应收账款转让确认书状态", related="t19_contract_info_id.state"
    )
    t19_contract_preview = fields.Binary(
        "应收账款转让确认书图片", related="t19_contract_info_id.contract_preview"
    )

    d09_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应付账款结清证明"
    )
    d09_contract_name = fields.Char(
        "应付账款结清证明", related="d09_contract_info_id.name"
    )
    d09_contract_pdf = fields.Binary(
        "应付账款结清证明", related="d09_contract_info_id.contract"
    )
    d09_contract_state = fields.Selection(
        "应付账款结清证明状态", related="d09_contract_info_id.state"
    )
    d09_contract_preview = fields.Binary(
        "应付账款结清证明图片", related="d09_contract_info_id.contract_preview"
    )

    t20_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应付账款转让确认书"
    )
    t20_contract_name = fields.Char(
        "应付账款转让确认书", related="t20_contract_info_id.name"
    )
    t20_contract_pdf = fields.Binary(
        "应收账款转让确认书", related="t20_contract_info_id.contract"
    )
    t20_contract_state = fields.Selection(
        "应收账款转让确认书状态", related="t20_contract_info_id.state"
    )
    t20_contract_preview = fields.Binary(
        "应付账款转让确认书图片", related="t20_contract_info_id.contract_preview"
    )

    c10_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="还款催告书"
    )
    c10_contract_name = fields.Char(
        "还款催告书", related="c10_contract_info_id.name"
    )
    c10_contract_pdf = fields.Binary(
        "还款催告书", related="c10_contract_info_id.contract"
    )
    c10_contract_state = fields.Selection(
        "还款催告书状态", related="c10_contract_info_id.state"
    )
    c10_contract_preview = fields.Binary(
        "还款催告书图片", related="c10_contract_info_id.contract_preview"
    )

    c11_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="律师催收函"
    )
    c11_contract_name = fields.Char(
        "律师催收函", related="c11_contract_info_id.name"
    )
    c11_contract_pdf = fields.Binary(
        "律师催收函", related="c11_contract_info_id.contract"
    )
    c11_contract_state = fields.Selection(
        "律师催收函状态", related="c11_contract_info_id.state"
    )
    c11_contract_preview = fields.Binary(
        "律师催收函图片", related="c11_contract_info_id.contract_preview"
    )

    c12_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应收账款回转通知书"
    )
    c12_contract_name = fields.Char(
        "应收账款回转通知书", related="c12_contract_info_id.name"
    )
    c12_contract_pdf = fields.Binary(
        "应收账款回转通知书", related="c12_contract_info_id.contract"
    )
    c12_contract_state = fields.Selection(
        "应收账款回转通知书状态", related="c12_contract_info_id.state"
    )
    c12_contract_preview = fields.Binary(
        "应收账款回转通知书图片", related="c12_contract_info_id.contract_preview"
    )

    c13_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应收账款熔断通知书"
    )
    c13_contract_name = fields.Char(
        "应收账款熔断通知书", related="c13_contract_info_id.name"
    )
    c13_contract_pdf = fields.Binary(
        "应收账款熔断通知书", related="c13_contract_info_id.contract"
    )
    c13_contract_state = fields.Selection(
        "应收账款熔断通知书状态", related="c13_contract_info_id.state"
    )
    c13_contract_preview = fields.Binary(
        "应收账款熔断通知书图片", related="c13_contract_info_id.contract_preview"
    )

    c14_contract_info_id = fields.Many2one(
        "ifs.contract.info", string="应收账款回转告知函"
    )
    c14_contract_name = fields.Char(
        "应收账款回转告知函", related="c14_contract_info_id.name"
    )
    c14_contract_pdf = fields.Binary(
        "应收账款回转告知函", related="c14_contract_info_id.contract"
    )
    c14_contract_state = fields.Selection(
        "应收账款回转告知函状态", related="c14_contract_info_id.state"
    )
    c14_contract_preview = fields.Binary(
        "应收账款回转告知函图片", related="c14_contract_info_id.contract_preview"
    )

    def daliy_cut_off(self):
        super().daliy_cut_off()
        for bill in self:
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
            if bill.state == "pending":
                if not bill.t19_contract_info_id.id:
                    params = json.dumps(
                        {
                            "t17_contract_code": str(
                                bill.sub_loan_account_id.factor_supplier_id.t17_contract_info_id.code
                            ),
                            "bill_code": str(bill.code),
                            "bill_amount": str(bill.bill_amount),
                            "bill_cycle": f'{start_bill_date_local.strftime("%Y年%m月%d日")} - {end_bill_date_local.strftime("%Y年%m月%d日")}',
                            "bill_day": bill_date_local.strftime("%Y年%m月%d日"),
                            "repayment_day": repayment_date_local.strftime(
                                "%Y年%m月%d日"
                            ),
                            "product_scope": bill.sub_loan_account_id.factor_supplier_id.product_scope,
                            "available_quota": bill.sub_loan_account_id.available_quota,
                        }
                    )
                    t19_template = self.env["ifs.contract.template"].retrieve_by_code(
                        "T19B", bill.factor_id.id, bill.supplier_id.id
                    )
                    t19_contract_info = self.env["ifs.contract.info"].create(
                        {
                            "name": t19_template.name,
                            "partner_one": "%s,%d"
                            % (bill.factor_id._name, bill.factor_id.id),
                            "partner_two": "%s,%d"
                            % (bill.supplier_id._name, bill.supplier_id.id),
                            "partner_three": "%s,%d"
                            % (bill.merchant_id._name, bill.merchant_id.id),
                            "template_id": t19_template.id,
                            "params": params,
                            "partner_two_signature": bill.supplier_id.signature,
                        }
                    )
                    bill.t19_contract_info_id = t19_contract_info
                if not bill.t20_contract_info_id:
                    params = json.dumps(
                        {
                            "t18_contract_code": str(
                                bill.sub_loan_account_id.t18_contract_info_id.code
                            ),
                            "bill_code": str(bill.code),
                            "bill_amount": str(bill.bill_amount),
                            "bill_cycle": f'{start_bill_date_local.strftime("%Y年%m月%d日")} - {end_bill_date_local.strftime("%Y年%m月%d日")}',
                            "bill_day": bill_date_local.strftime("%Y年%m月%d日"),
                            "repayment_day": repayment_date_local.strftime(
                                "%Y年%m月%d日"
                            ),
                            "product_scope": bill.sub_loan_account_id.factor_supplier_id.sudo().product_scope,
                            "available_quota": bill.sub_loan_account_id.available_quota,
                        }
                    )
                    t20_template = self.env["ifs.contract.template"].retrieve_by_code(
                        "T20B", bill.factor_id.id, bill.supplier_id.id
                    )
                    t20_contract_info = self.env["ifs.contract.info"].create(
                        {
                            "name": t20_template.name,
                            "partner_one": "%s,%d"
                            % (bill.factor_id._name, bill.factor_id.id),
                            "partner_two": "%s,%d"
                            % (bill.merchant_id._name, bill.merchant_id.id),
                            "partner_three": "%s,%d"
                            % (bill.supplier_id._name, bill.supplier_id.id),
                            "template_id": t20_template.id,
                            "params": params,
                            "partner_two_signature": bill.merchant_id.signature,
                        }
                    )
                    bill.t20_contract_info_id = t20_contract_info
                elif bill.t20_contract_info_id.state not in [
                    "committed",
                    "signed",
                ] and bill.bill_date < fields.Datetime.now() - timedelta(days=1):
                    # TODO: 自动签名
                    bill.t19_contract_info_id.write(
                        {
                            "partner_two_signature": bill.supplier_id.signature,
                        }
                    )
                    bill.t19_contract_info_id.signature_all()
                    bill.t20_contract_info_id.write(
                        {
                            "partner_two_signature": bill.merchant_id.signature,
                        }
                    )
                    bill.t20_contract_info_id.signature_all()
            elif bill.state == 'overdue':
                if not bill.c10_contract_info_id and bill.t20_contract_info_id:
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
                    c10_template = self.env["ifs.contract.template"].retrieve_by_code(
                        "C10", bill.factor_id.id, bill.supplier_id.id
                    )
                    c10_contract_info = self.env["ifs.contract.info"].create(
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
                    bill.c10_contract_info_id = c10_contract_info
                    bill.c10_contract_info_id.signature_all()
