# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecReviewMerchantAuditing(models.TransientModel):
    _name = 'ifs.gar.review.merchant.auditing.wizard'
    _description = "保理方审核"

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='审批流程')
    company_id = fields.Many2one(
        'res.company', string='公司', related='entry_id.company_id')
    user_company_id = fields.Many2one(
        'res.company', string='公司', default=lambda self: self.env.user.company_id)
    entry_date = fields.Datetime(related='entry_id.entry_date', string="进件时间")
    # 商业保理风控评估意见
    factor_approval_user_id = fields.Many2one(
        'res.users', '审批人', related='entry_id.factor_approval_user_id', readonly=False, required=True, default=lambda self: self.env.user.id)
    factor_approval_opinion_output = fields.Selection(
        '审批意见输出', related='entry_id.factor_approval_opinion_output', readonly=False, required=True)
    factor_business_base = fields.Selection(
        '企业基本面', related='entry_id.factor_business_base', readonly=False, required=True)
    factor_business_risk = fields.Selection(
        '企业风险', related='entry_id.factor_business_risk', readonly=False, required=True)
    factor_legal_person_risk = fields.Selection(
        '法人风险', related='entry_id.factor_legal_person_risk', readonly=False, required=True)
    factor_guarantor_name_risk = fields.Selection(
        '担保人风险', related='entry_id.factor_guarantor_name_risk', readonly=False, required=True)
    factor_other_risk = fields.Selection(
        '其他风险', related='entry_id.factor_other_risk', readonly=False, required=True)
    factor_approval_opinion = fields.Html(
        '审批意见', related='entry_id.factor_approval_opinion', readonly=False, store=True)

    def action_save(self):
        pass

    def action_confirm(self):
        if self.entry_id.id:
            self.entry_id.write({
                'state': 'approve',
                'factor_approval_time': fields.Datetime.now(),
            })
            if self.entry_id.create_from == 'open_api':
                message_body = {
                    'approval_info': {
                        'entry_code': self.entry_id.seq_code,
                        'state': 'approve',
                        'empty_list': [],
                        'account_info': None
                    }
                }
                self.entry_id.message_handler(message_body)
        else:
            raise AccessDenied(_('无法找到审批流程'))
