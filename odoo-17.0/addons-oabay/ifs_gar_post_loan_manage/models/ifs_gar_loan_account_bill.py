# -*- coding: utf-8 -*-


from odoo import models, fields


class InclusiveFinancingLoanAccountBill(models.Model):
    _inherit = "ifs.gar.loan.account.bill"

    t24_contract_info_id = fields.Many2one("ifs.contract.info", string="展期合同")
    t24_contract_name = fields.Char("展期合同名称", related="t24_contract_info_id.name")
    t24_contract_pdf = fields.Binary("展期合同文件", related="t24_contract_info_id.contract")
    t24_contract_state = fields.Selection("展期合同状态", related="t24_contract_info_id.state")
    t24_contract_preview = fields.Binary("展期合同图片预览", related="t24_contract_info_id.contract_preview")
