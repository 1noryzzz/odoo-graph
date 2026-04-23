# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingBaseCompany(models.Model):
    _inherit = 'ifs.base.company'

    signature = fields.Image(
        '保理方签名', compute='_compute_factor_info',
        groups='ifs_partner.group_ifs_partner_factor_system')

    guarantor_employee_id = fields.Many2one(
        'hr.employee', string='担保人', ondelete='restrict')

    reception_picture = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='前台照')
    office_area_picture = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='公司办公区照片')
    lease_contract = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='租赁合同')
    half_year_balance_sheet = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='近半年的资产负债表')
    half_year_cash_flow_sheet = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='近半年现金流量表')
    half_year_assets_gains_losses_sheet = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='近半年资产损益表')
    enterprise_property_certificate = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='企业名下相关财产证明')

    def has_ifs_partner(self, ifs_partner):
        return ifs_partner in (self.company_id.ifs_partners or [])

    def _doc_mapping(self):
        return {
            **super()._doc_mapping(),
            'reception_picture': 'reception',
            'office_area_picture': 'office_area_picture',
            'lease_contract': 'lease_contract',
            'half_year_balance_sheet': 'half_year_balance_sheet',
            'half_year_cash_flow_sheet': 'half_year_cash_flow_sheet',
            'half_year_assets_gains_losses_sheet': 'half_year_assets_gains_losses_sheet',
            'enterprise_property_certificate': 'enterprise_property_certificate',
        }

    @api.depends('ifs_partner_factor_ids')
    def _compute_factor_info(self):
        for record in self:
            factor_info = {
                'factor_code': False,
                'signature': False
            }
            if record.ifs_partner_factor_ids:
                factor = record.ifs_partner_factor_ids[0]
                factor_info.update({
                    'factor_code': factor.seq_code,
                    'signature': factor.signature
                })
            record.update(factor_info)

    def create_or_update_sign(self):
        if self.ifs_partner_factor_ids:
            factor = self.ifs_partner_factor_ids[0]
            factor._prepare_sign(sign_name=self.legal_id.name)
            return {
                'name': '更新保理方存留签名',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'ifs.partner.factor.sign.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_factor_id': factor.id,
                    'default_sign_url': factor.sign_url,
                }
            }


class InclusiveFinancingBaseCompanyDoc(models.Model):
    _inherit = 'ifs.base.company.doc'

    name = fields.Selection(selection_add=[
        ('reception', '前台照'),
        ('office_area_picture', '公司办公区照片'),
        ('lease_contract', '租赁合同'),
        ('half_year_balance_sheet', '近半年的资产负债表'),
        ('half_year_cash_flow_sheet', '近半年现金流量表'),
        ('half_year_assets_gains_losses_sheet', '近半年资产损益表'),
        ('enterprise_property_certificate', '企业名下相关财产证明'),
    ], ondelete={
        'reception': 'cascade',
        'office_area_picture': 'cascade',
        'lease_contract': 'cascade',
        'half_year_balance_sheet': 'cascade',
        'half_year_cash_flow_sheet': 'cascade',
        'half_year_assets_gains_losses_sheet': 'cascade',
        'enterprise_property_certificate': 'cascade',
    })
