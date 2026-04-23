# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsUpgradeQuotaApply(models.Model):
    _name = 'ifs.gar.upgrade.quota.apply'
    _inherit = ['ifs.ir.sequence.mixin']
    _inherits = {'ifs.base.company': 'ifs_company_id'}
    _description = '采购方提额申请'

    state = fields.Selection([
        ('draft', '草稿'),
        ('committed', '已提交'),
        ('approve', '待确认'),
        ('approval', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    json_datas = fields.Properties(
        '工商登记信息', definition='definition_id.params_definition', related='ifs_company_id.json_datas')

    sub_loan_account_id = fields.Many2one(
        'ifs.gar.sub.loan.account', required=True, ondelete='restrict', index=True)
    factor_id = fields.Many2one(
        'ifs.partner.factor', related='sub_loan_account_id.factor_id')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', related='sub_loan_account_id.supplier_id')
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', related='sub_loan_account_id.merchant_id')
    merchant_code = fields.Char('采购方编号', related='merchant_id.seq_code')
    account_code = fields.Char(
        '贷款账户编号', related='sub_loan_account_id.seq_code')
    currency_id = fields.Many2one(
        'res.currency', string='币种', related='sub_loan_account_id.currency_id')

    origin_quota = fields.Monetary(
        '原额度', related='sub_loan_account_id.approved_quota')
    apply_quota = fields.Monetary('申请额度', required=True)
    apply_reason = fields.Text('调整原因', required=True)
    apply_basis = fields.Text('调整依据', required=True)
    
    factor_can_confirm = fields.Boolean('保理方可确认或取消', compute="_compute_factor_can_confirm")
    supplier_can_confirm = fields.Boolean('供应方可确认或取消', compute="_compute_supplier_can_confirm")
    merchant_can_confirm = fields.Boolean('采购方可提交', compute="_compute_merchant_can_confirm")

    reject_reason = fields.Text('拒绝原因')
    
    commit_datetime = fields.Datetime('提交时间')
    approval_datetime = fields.Datetime('审批时间')
    
    @api.depends('state')
    def _compute_factor_can_confirm(self):
        for record in self:
            record.factor_can_confirm = (
                record.factor_id.company_id.id == self.env.company.id and
                record.state =='approve')
            
    @api.depends('state')
    def _compute_supplier_can_confirm(self):
        for record in self:
            record.supplier_can_confirm = (
                record.supplier_id.company_id.id == self.env.company.id and
                record.state =='committed')
            
    @api.depends('state')
    def _compute_merchant_can_confirm(self):
        for record in self:
            record.merchant_can_confirm = (
                record.merchant_id.company_id.id == self.env.company.id and
                record.state =='draft')

    @api.model
    def start_apply_quota(self, sub_loan_account):
        exist_apply = self.search([
            ('sub_loan_account_id', '=', sub_loan_account.id),
            ('state', 'not in', ['approval', 'rejected'])
        ], limit=1)

        return {
            'name': _('申请调整额度'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.gar.upgrade.quota.apply',
            'res_id': exist_apply.id,
            'target': 'new',
            'context': {
                'default_sub_loan_account_id': sub_loan_account.id,
                'default_ifs_company_id': sub_loan_account.merchant_id.ifs_company_id.id,
            }
        }

    def action_commit(self):
        self.ensure_one()
        if self.merchant_can_confirm:
            self.commit_datetime = fields.Datetime.now()
            self.state = 'committed'

    def action_factor_confirm(self):
        self.ensure_one()
        if self.factor_can_confirm:
            self.state = 'approval'

    def action_supplier_confirm(self):
        self.ensure_one()
        if self.supplier_can_confirm:
            self.state = 'approve'
            self.approval_datetime = fields.Datetime.now()

    def action_factor_refuse(self):
        self.ensure_one()
        if self.factor_can_confirm:
            self.state = 'rejected'

    def action_supplier_refuse(self):
        self.ensure_one()
        if self.supplier_can_confirm:
            self.state = 'rejected'
            self.approval_datetime = fields.Datetime.now()
