# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecReviewFranchiseeReject(models.TransientModel):
    _name = 'ifs.gar.review.franchisee.reject.wizard'
    _description = '拒绝合伙人进件'

    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', string='审批流程')
    reject_reason = fields.Html('拒绝原因', copy=False)

    def action_confirm(self):
        if self.entry_id:
            self.entry_id.write({
                'reject_reason': self.reject_reason,
                'state': 'rejected',
                'review_date': fields.Datetime.now(),
            })
        else:
            raise AccessDenied(_('无法找到审批流程'))
