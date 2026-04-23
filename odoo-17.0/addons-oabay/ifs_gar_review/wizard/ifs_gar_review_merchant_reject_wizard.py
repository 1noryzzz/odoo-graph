# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecReviewMerchantReject(models.TransientModel):
    _name = 'ifs.gar.review.merchant.reject.wizard'
    _description = '采购方进件审批拒绝向导'
    
    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='审批流程')
    reject_reason = fields.Html('拒绝原因-详情', required=True)
    reject_reason_simple = fields.Char('拒绝原因', required=True)
    
    def action_confirm(self):
        if self.entry_id:
            self.entry_id.write({
                'reject_reason': self.reject_reason,
                'reject_reason_simple': self.reject_reason_simple,
                'state': 'rejected',
                'supplier_approval_time': fields.Datetime.now(),
            })
            if self.entry_id.create_from == 'open_api':
                message_body = {
                    'approval_info': {
                        'entry_code': self.entry_id.seq_code,
                        'state': 'rejected',
                        'hint': self.reject_reason_simple,
                        'empty_list': [],
                        'account_info': None
                    }
                }
                self.entry_id.message_handler(message_body)