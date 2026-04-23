# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied

class GuaranteeAccountsRecReviewMerchantApprove(models.TransientModel):
    _name = 'ifs.gar.review.merchant.approve.wizard'
    _description = "供应方审核采购方进件并授信向导"

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='审批流程')
    company_id = fields.Many2one(
        'res.company', string='公司', related='entry_id.company_id')
    user_company_id = fields.Many2one(
        'res.company', string='公司', default=lambda self: self.env.user.company_id)
    entry_date = fields.Datetime(related='entry_id.entry_date', string="进件时间")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='entry_id.currency_id')
    # 供应商风控审批岗
    supplier_approval_user_id = fields.Many2one(
        'res.users', '审批人', related='entry_id.supplier_approval_user_id', readonly=False, required=True, default=lambda self: self.env.user.id)
    supplier_approval_opinion_output = fields.Selection(
        '审批意见输出', related='entry_id.supplier_approval_opinion_output', readonly=False, required=True)
    supplier_business_base = fields.Selection(
        '企业基本面', related='entry_id.supplier_business_base', readonly=False, required=True)
    supplier_business_risk = fields.Selection(
        '企业风险', related='entry_id.supplier_business_risk', readonly=False, required=True)
    supplier_legal_person_risk = fields.Selection(
        '法人风险', related='entry_id.supplier_legal_person_risk', readonly=False, required=True)
    supplier_guarantor_name_risk = fields.Selection(
        '担保人风险', related='entry_id.supplier_guarantor_name_risk', readonly=False, required=True)
    supplier_other_risk = fields.Selection(
        '其他风险', related='entry_id.supplier_other_risk', readonly=False, required=True)
    supplier_approval_opinion = fields.Html(
        '审批意见', related='entry_id.supplier_approval_opinion', readonly=False, required=True)
    supplier_approval_base = fields.Monetary(
        '审批基数', related='entry_id.supplier_approval_base', readonly=False, required=True)
    supplier_approval_multiple = fields.Float(
        '审批倍数', related='entry_id.supplier_approval_multiple', readonly=False, required=True)
    supplier_final_quota = fields.Monetary(
        '最终额度', compute='_compute_supplier_final_quota')
    credit_term = fields.Integer('账期(月)', related='entry_id.credit_term', readonly=False, required=True)
    repay_day = fields.Integer('还款日', related='entry_id.repay_day', readonly=False, required=True)
    # 供应商风控复核岗
    # supplier_review_time = fields.Datetime(
    #     '审批时间', related='entry_id.supplier_review_time', readonly=False, store=True)
    # supplier_review_name = fields.Char(
    #     '审批人', related='entry_id.supplier_review_name', readonly=False, store=True)
    # supplier_review_opinion_output = fields.Selection(
    #     '审批意见输出', related='entry_id.supplier_review_opinion_output', readonly=False, store=True)
    # review_business_base = fields.Selection(
    #     '企业基本面', related='entry_id.review_business_base', readonly=False, store=True)
    # review_business_risk = fields.Selection(
    #     '企业风险', related='entry_id.review_business_risk', readonly=False, store=True)
    # review_legal_person_risk = fields.Selection(
    #     '法人风险', related='entry_id.review_legal_person_risk', readonly=False, store=True)
    # review_guarantor_name_risk = fields.Selection(
    #     '担保人风险', related='entry_id.review_guarantor_name_risk', readonly=False, store=True)
    # review_other_risk = fields.Selection(
    #     '其他风险', related='entry_id.review_other_risk', readonly=False, store=True)
    # supplier_review_opinion = fields.Html(
    #     '审批意见', related='entry_id.supplier_review_opinion', readonly=False, store=True)
    # supplier_review_base = fields.Monetary(
    #     '审批基数', related='entry_id.supplier_review_base', readonly=False, store=True)
    # supplier_review_multiple = fields.Float(
    #     '审批倍数', related='entry_id.supplier_review_multiple', readonly=False, store=True)
    # review_final_quota = fields.Monetary(
    #     '最终额度', related='merchant_id.review_final_quota', readonly=False, store=True)

    @api.depends('supplier_approval_base', 'supplier_approval_multiple')
    def _compute_supplier_final_quota(self):
        for record in self:
            if record.supplier_approval_base and record.supplier_approval_multiple:
                record.supplier_final_quota = record.supplier_approval_base * \
                    record.supplier_approval_multiple
            else:
                record.supplier_final_quota = 0.0

    def action_save(self):
        pass

    def action_confirm(self):
        if self.entry_id.id:
            self.entry_id.write({
                'state': 'approval',
                'supplier_approval_time': fields.Datetime.now(),
                'supplier_final_quota': self.supplier_final_quota,
                'credit_term': self.credit_term,
                'repay_day': self.repay_day,
            })
        else:
            raise AccessDenied(_('无法找到审批流程'))
