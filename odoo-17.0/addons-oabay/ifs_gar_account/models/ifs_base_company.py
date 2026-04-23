# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class InclusiveFinancingBaseCompany(models.Model):
    _inherit = 'ifs.base.company'

    merchant_approved_quota = fields.Monetary(
        '授信额度', compute='_compute_merchant_info')
    merchant_available_quota = fields.Monetary(
        '可用额度', compute='_compute_merchant_info')
    merchant_freeze_quota = fields.Monetary(
        '冻结额度', compute='_compute_merchant_info')
    merchant_used_quota = fields.Monetary(
        '已用额度', compute='_compute_merchant_info')

    supplier_total_quota = fields.Monetary(
        compute='_compute_supplier_info', string='供应方总额度')
    supplier_approved_quota = fields.Monetary(
        compute='_compute_supplier_info', string='供应方已审批额度')

    @api.depends('ifs_partner_merchant_ids')
    def _compute_merchant_info(self):
        super()._compute_merchant_info()
        for record in self:
            merchant_info = {
                'merchant_approved_quota': 0.00,
                'merchant_available_quota': 0.00,
                'merchant_freeze_quota': 0.00,
                'merchant_used_quota': 0.00,
            }
            if record.ifs_partner_merchant_ids:
                merchant = record.ifs_partner_merchant_ids[0]
                merchant_info.update({
                    'merchant_approved_quota': merchant.approved_quota,
                    'merchant_available_quota': merchant.available_quota,
                    'merchant_freeze_quota': merchant.freeze_quota,
                    'merchant_used_quota': merchant.used_quota,
                })
            record.update(merchant_info)

    @api.depends('ifs_partner_supplier_ids')
    def _compute_supplier_info(self):
        super()._compute_supplier_info()

        for record in self:
            supplier_info = {
                'supplier_total_quota': 0.00,
                'supplier_approved_quota': 0.00
            }
            if record.ifs_partner_supplier_ids:
                supplier = record.ifs_partner_supplier_ids[0]
                supplier_info.update({
                    'supplier_total_quota': supplier.total_quota,
                    'supplier_approved_quota': supplier.approved_quota,
                })
            record.update(supplier_info)

    #子账户
    def view_merchant_quota_info(self):
        self.ensure_one()
        merchant_id = self.env['ifs.partner.merchant'].search([('ifs_company_id', '=', self.id)])
        if merchant_id:
            return {
                'name': _('子账户列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.sub.loan.account',
                'res_id': False,
                'domain': [('merchant_id', '=', merchant_id.id)],
                'target': 'current',
            }

    #关联关系
    def view_supplier_quota_info(self):
        self.ensure_one()
        supplier_id = self.env['ifs.partner.supplier'].search([('ifs_company_id', '=', self.id)])
        if supplier_id:
            return {
                'name': _('保理方和供应方关联关系列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'res_model': 'ifs.gar.partner.factor.supplier',
                'res_id': False,
                'domain': [('supplier_id', '=', supplier_id.id)],
                'target': 'current',
            }

    #子账户
    def view_loan_account_info(self):
        self.ensure_one()
        supplier_id = self.env['ifs.partner.supplier'].search([('ifs_company_id', '=', self.id)])
        if supplier_id:
            return {
                'name': _('子账户列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.sub.loan.account',
                'res_id': False,
                'domain': [('supplier_id', '=', supplier_id.id)],
                'target': 'current',
            }

    #订单
    def view_sub_loan_account_info(self):
        pass

    def action_apply_upgrade_quota(self):
        if 'merchant' in (self.env.company.ifs_partners or []) and self.ifs_partner_merchant_ids:
            merchant = self.ifs_partner_merchant_ids[0]
            if not merchant.id or len(merchant.sub_loan_account_ids.filtered(lambda sa: sa.state == 'normal') if merchant.sub_loan_account_ids else []) == 0:
                raise AccessDenied(_('当前采购方暂无已开通的贷款账户！'))

            sub_loan_account_ids = merchant.sub_loan_account_ids.filtered(
                lambda sa: sa.state == 'normal')
            if len(sub_loan_account_ids) >= 1:
                return {
                    'name': _('选择此次申请调整额度的子账户'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'ifs.gar.sub.loan.account',
                    'res_id': False,
                    'target': 'new',
                    'domain': [('id', 'in', sub_loan_account_ids.ids)],
                    'views': [
                        [self.env.ref(
                            'ifs_gar_account.ifs_gar_sub_loan_account_view_selector').id, 'tree']
                    ],
                }
            else:
                return self.env['ifs.gar.upgrade.quota.apply'].start_apply_quota(sub_loan_account_ids)
        else:
            raise AccessDenied(_('仅限采购方操作！'))
