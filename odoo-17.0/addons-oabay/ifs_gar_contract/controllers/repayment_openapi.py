# -*- coding: utf-8 -*-

from ast import Bytes
import datetime

from odoo import _, http, fields
from odoo.http import request
from odoo.http import content_disposition, request
from odoo.exceptions import AccessDenied, UserError
from dateutil.relativedelta import relativedelta
import base64, io
import json
import dateutil

from odoo.addons.ifs_gar_repayment.controllers.openapi import OpenApiController


class InclusiveFinancingRepaymentOpenApi(OpenApiController):

    @http.route()
    def do_repay(
        self,
        merchant_code,
        bill_code,
        repay_amount,
        operate_type="repayment",
        remark=None,
    ):
        result = super().do_repay(
            merchant_code, bill_code, repay_amount, operate_type, remark
        )

        repayment_order = request.env["ifs.gar.repayment.order"].search(
            [
                ("seq_code", "=", result.get("repayment_code")),
                ("merchant_code", "=", merchant_code),
                ("bill_code", "=", bill_code),
            ]
        )
        if repayment_order.bill_id.is_bill_paided() and repayment_order.bill_id.bill_amount > 0:
            if not repayment_order.bill_id.d08_contract_info_id.id:
                params = json.dumps({
                    't19_contract_date': repayment_order.bill_id.t19_contract_info_id.sign_date.strftime('%Y年%m月%d日'),
                    't19_contract_code': repayment_order.bill_id.t19_contract_info_id.code,
                    'accounts': repayment_order.bill_id.bill_amount
                })
                d08_template = request.env['ifs.contract.template'].retrieve_by_code('D08', repayment_order.bill_id.factor_id.id)
                d08_contract_info = request.env['ifs.contract.info'].create({
                    'name': d08_template.name,
                    'partner_one': '%s,%d' % (repayment_order.bill_id.factor_id._name, repayment_order.bill_id.factor_id.id),
                    'partner_two': '%s,%d' % (repayment_order.bill_id.supplier_id._name, repayment_order.bill_id.supplier_id.id),
                    'template_id': d08_template.id,
                    'params': params,
                })
                repayment_order.bill_id.write({
                    'd08_contract_info_id': d08_contract_info.id,
                })
            else:
                repayment_order.bill_id.d08_contract_info_id.write({
                    'params': params,
                })

            if not repayment_order.bill_id.d09_contract_info_id.id:
                params = json.dumps({
                    'partner_one_name': repayment_order.bill_id.merchant_id.name,
                    'partner_two_name': repayment_order.bill_id.factor_id.name,
                    't20_contract_date': repayment_order.bill_id.t20_contract_info_id.sign_date.strftime('%Y年%m月%d日'),
                    't20_contract_code': repayment_order.bill_id.t20_contract_info_id.code,
                    'accounts': repayment_order.bill_id.bill_amount
                })
                d09_template = request.env['ifs.contract.template'].retrieve_by_code('D09', repayment_order.bill_id.factor_id.id)
                d09_contract_info = request.env['ifs.contract.info'].create({
                    'name': d09_template.name,
                    'partner_one': '%s,%d' % (repayment_order.bill_id.merchant_id._name, repayment_order.bill_id.merchant_id.id),
                    'partner_two': '%s,%d' % (repayment_order.bill_id.factor_id._name, repayment_order.bill_id.factor_id.id),
                    'template_id': d09_template.id,
                    'params': params,
                })
                repayment_order.bill_id.write({
                    'd09_contract_info_id': d09_contract_info.id,
                })
            else:
                repayment_order.bill_id.d09_contract_info_id.write({
                    'params': params,
                })

            repayment_order.bill_id.d09_contract_info_id.signature_all()
            repayment_order.bill_id.d08_contract_info_id.signature_all()

            # TODO: 如果已还完，签D08 应收账款结清证明，和D09 应付账款结清证明 并更新账单状态为 settle 已结清
            repayment_order.bill_id.state = 'settle'
        # if repayment_order.state == "repaid":
        #     repayment_order.bill_id.action_settle()

        result.get('bill_info').update({
            'state': repayment_order.bill_id.state,
        })

        return result
