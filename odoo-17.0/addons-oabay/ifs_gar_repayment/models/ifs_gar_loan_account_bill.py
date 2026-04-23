# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingLoanAccountBill(models.Model):
    _inherit = "ifs.gar.loan.account.bill"

    def daliy_cut_off(self):
        has_overdue = super().daliy_cut_off()
        if has_overdue:
            for bill in self:
                if bill.state == "overdue":
                    plan = self.env["ifs.gar.payment.plan"].search(
                        [("bill_id", "=", bill.id)], limit=1
                    )
                    if plan:
                        plan.state = "overdue"

        return has_overdue


class InclusiveFinancingLoanAccountBillLog(models.Model):
    _inherit = "ifs.gar.loan.account.bill.log"

    order_id = fields.Reference(
        selection_add=[
            ("ifs.gar.repayment.order", "还款单"),
        ]
    )
