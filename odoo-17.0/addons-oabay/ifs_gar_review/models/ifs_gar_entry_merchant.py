# -*- coding: utf-8 -*-

import time
import requests
import logging

from odoo import _, api, models, fields, Command
from odoo.exceptions import AccessDenied, UserError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecEntryMerchant(models.Model):
    _inherit = 'ifs.gar.entry.merchant'

    review_date = fields.Datetime('审批时间', copy=False)
    btw_reason = fields.Html('驳回原因', copy=False)
    btw_reason_simple = fields.Char('驳回原因', copy=False)
    reject_reason = fields.Html('拒绝原因', copy=False)
    reject_reason_simple = fields.Char('拒绝原因', copy=False)
    approved_quota = fields.Monetary('授信额度')
    system_valuation = fields.Char(string='系统评估', default='A+')

    # 商业保理风控评估意见
    factor_approval_time = fields.Datetime('审批时间')
    factor_approval_user_id = fields.Many2one(
        'res.users', '审批人', copy=False, ondelete='restrict')
    factor_approval_opinion_output = fields.Selection([
        ('adopt', '通过'),
        ('secondary', '次级'),
        ('review', '复核'),
    ], string='审批意见输出')
    factor_business_base = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='企业基本面')
    factor_business_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='企业风险')
    factor_legal_person_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='法人风险')
    factor_guarantor_name_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='担保人风险')
    factor_other_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='其他风险')
    factor_approval_opinion = fields.Html('审批意见')
    # 供应商风控审批岗
    supplier_approval_time = fields.Datetime('审批时间')
    supplier_approval_user_id = fields.Many2one(
        'res.users', '审批人', copy=False, ondelete='restrict')
    supplier_approval_opinion_output = fields.Selection([
        ('adopt', '通过'),
        ('secondary', '次级'),
        ('review', '复核'),
        ('abandon', '舍弃'),
    ], string='审批意见输出')
    supplier_business_base = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='企业基本面')
    supplier_business_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='企业风险')
    supplier_legal_person_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='法人风险')
    supplier_guarantor_name_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='担保人风险')
    supplier_other_risk = fields.Selection([
        ('ad', 'AD'),
        ('cm', 'CM'),
        ('ut', 'UT')
    ], string='其他风险')
    supplier_approval_opinion = fields.Html('审批意见')
    supplier_approval_base = fields.Monetary('审批基数', default=300000.0)
    supplier_approval_multiple = fields.Float('审批倍数', default=1.0)
    supplier_final_quota = fields.Monetary('最终额度')
    # # 供应商风控复核岗
    # supplier_review_time = fields.Datetime('审批时间')
    # supplier_review_name = fields.Many2one(
    #   'res.users', '审批人', copy=False, ondelete='restrict')
    # supplier_review_opinion_output = fields.Selection([
    #     ('adopt', '通过'),
    #     ('abandon', '舍弃'),
    # ], string='审批意见输出')
    # review_business_base = fields.Selection([
    #     ('ad', 'AD'),
    #     ('cm', 'CM'),
    #     ('ut', 'UT')
    # ], string='企业基本面')
    # review_business_risk = fields.Selection([
    #     ('ad', 'AD'),
    #     ('cm', 'CM'),
    #     ('ut', 'UT')
    # ], string='企业风险')
    # review_legal_person_risk = fields.Selection([
    #     ('ad', 'AD'),
    #     ('cm', 'CM'),
    #     ('ut', 'UT')
    # ], string='法人风险')
    # review_guarantor_name_risk = fields.Selection([
    #     ('ad', 'AD'),
    #     ('cm', 'CM'),
    #     ('ut', 'UT')
    # ], string='担保人风险')
    # review_other_risk = fields.Selection([
    #     ('ad', 'AD'),
    #     ('cm', 'CM'),
    #     ('ut', 'UT')
    # ], string='其他风险')
    # supplier_review_opinion = fields.Html('审批意见')
    # supplier_review_base = fields.Monetary('审批基数', default=5000.0)
    # supplier_review_multiple = fields.Float('审批倍数', default=1.0)
    # is_supplier_approval = fields.Boolean('供应商风控是否审核', default=False)
    
    factor_can_confirm = fields.Boolean('保理方可确认', compute="_compute_factor_can_confirm")
    supplier_can_confirm = fields.Boolean('供应方可确认', compute="_compute_supplier_can_confirm")
    
    @api.depends('state')
    def _compute_factor_can_confirm(self):
        for record in self:
            record.factor_can_confirm = (
                record.factor_id.company_id.id == self.env.company.id and
                record.state == 'committed')
            
    @api.depends('state')
    def _compute_supplier_can_confirm(self):
        for record in self:
            record.supplier_can_confirm = (
                record.supplier_id.company_id.id == self.env.company.id and
                record.state == 'approve')

    def write(self, vals):
        if 'state' in vals and vals.get('state') in ['btw', 'approve', 'rejected', 'approval'] and not self.review_date:
            vals['review_date'] = fields.Datetime.now()
        return super().write(vals)

    def start_step(self):
        if self.state in ['btw', 'rejected', 'approval']:
            first_model = f'ifs.gar.entry.merchant.{self.state}.info.wizard'
            return {
                'name': self.env[first_model]._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': first_model,
                'res_id': False,
                'target': 'current',
                'context': {
                    f'default_{self._ref_id_field}': self.id,
                }
            }
        return super().start_step()

    def confirm_merchant(self):
        self.ensure_one()

        # 把进件向导录入的信息更新到当前进件的公司全局信息中
        self.ifs_company_id.sudo().write({
            'phone': self.phone,
            'email': self.email,
            'business_address': self.business_address,
            'business_license': self.business_license,
            'charter': self.charter,
            'reception_picture': self.reception_picture,
            'office_area_picture': self.office_area_picture,
            'lease_contract': self.lease_contract,
            'half_year_balance_sheet': self.half_year_balance_sheet,
            'half_year_cash_flow_sheet': self.half_year_cash_flow_sheet,
            'half_year_assets_gains_losses_sheet': self.half_year_assets_gains_losses_sheet,
            'enterprise_property_certificate': self.enterprise_property_certificate,
            'last_risk_credit_id': self.ifs_risk_credits_id,
            'last_guarantor_risk_credit_id': self.guarantor_ifs_risk_credits_id,
        })

        factor_supplier_id = self.env['ifs.gar.partner.factor.supplier'].sudo().search([
            ('factor_id', '=', self.factor_id.id),
            ('supplier_id', '=', self.supplier_id.id),
        ], limit=1)
        if not factor_supplier_id.exists():
            raise AccessDenied('邀请您进件的供应方当前状态不可用！')

        factor_merchant_sudo = self.env['ifs.gar.partner.factor.merchant'].sudo(
        )
        supplier_merchant_data = {
            'entry_id': self.id,
            'factor_supplier_id': factor_supplier_id.id,
        }
        factor_merchant = False
        merchant = self.env['ifs.partner.merchant'].search([
            ('ifs_company_id', '=', self.ifs_company_id.id)], limit=1)
        if merchant.exists():
            factor_merchant = factor_merchant_sudo.search([
                ('factor_id', '=', self.factor_id.id),
                ('merchant_id', '=', merchant.id),
            ], limit=1)
        else:
            merchant = self.env['ifs.partner.merchant'].sudo().create({
                'ifs_company_id': self.ifs_company_id.id,
            })

        if not factor_merchant or not factor_merchant.id:
            factor_merchant = factor_merchant_sudo.create({
                'factor_id': self.factor_id.id,
                'merchant_id': merchant.id,
            })

        supplier_merchant_data.update({
            'merchant_id': merchant.id,
        })
        self.env['ifs.gar.partner.supplier.merchant'].sudo().create(
            supplier_merchant_data)

        if self.create_from != 'open_api':
            # 更新法人信息
            idcard = self.env['hr.employee.idcard'].sudo(
            ).create_legal_from_entry(self)
            self.root_employee_id.sudo().write({
                'gender': idcard.gender,
                'birthday': idcard.birthday,
                'idcard_id': idcard.id,
            })

            if not self.is_self_guarantee:
                # 更新担保人信息
                if self.guarantor_employee_id.id and self.guarantor_employee_id.name != self.guarantor_name:
                    raise AccessDenied(_('担保人姓名与系统中的担保人姓名不一致！'))

                idcard = self.env['hr.employee.idcard'].sudo(
                ).create_guarantor_from_entry(self)
                if self.guarantor_employee_id.id:
                    self.guarantor_employee_id.sudo().write({
                        'gender': idcard.gender,
                        'birthday': idcard.birthday,
                        'idcard_id': idcard.id,
                    })
                else:
                    default_wp = self.env['ifs.work.position'].sudo().search([
                        ('company_id', '=', self.company_id.id),
                        ('code', '=', 'SYSTEM')
                    ], limit=1)
                    mobile = self.guarantor_info.get('guarantor_phone') if self.guarantor_info else False
                    partner = self.env['res.partner'].search([
                        ('parent_id', '=', self.partner_id.id),
                        ('name', '=', self.guarantor_name)])
                    if not partner.exists():
                        partner = self.env['res.partner'].create({
                            'name': self.guarantor_name,
                            'phone': mobile,
                            'mobile': mobile,
                            'parent_id': self.partner_id.id
                        })
                    user_info = {
                        'name': self.guarantor_name,
                        'login': f'{self.ifs_company_id.seq_code}_{int(time.time())}',
                        'mobile_phone': mobile,
                        'work_position_ids': [Command.link(default_wp.id)],
                        'state': 'paused',
                        'company_id': self.company_id.id,
                        'user_partner_id': self.principal_id.id,
                        'is_root': False,
                    }
                    guarantor_employee = self.env['hr.employee'].sudo().create(
                        user_info)
                    self.ifs_company_id.sudo().write({
                        'principal_id': partner.id,
                        'guarantor_employee_id': guarantor_employee.id
                    })

        return merchant

    def action_auditing(self):
        if self.factor_can_confirm:
            return {
                'name': '保理方审核',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.review.merchant.auditing.wizard',
                'target': 'new',
                'context': {
                    'default_entry_id': self.id,
                }
            }

    def action_approve(self):
        if self.supplier_can_confirm:
            return {
                'name': '供应方授信',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.review.merchant.approve.wizard',
                'target': 'new',
                'context': {
                    'default_entry_id': self.id,
                }
            }

    def action_btw(self):
        if self.factor_can_confirm:
            return {
                'name': '驳回采购方进件',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.review.merchant.btw.wizard',
                'target': 'new',
                'context': {
                    'default_entry_id': self.id,
                }
            }

    def action_reject(self):
        if self.supplier_can_confirm:
            return {
                'name': '拒绝给采购方授信',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.review.merchant.reject.wizard',
                'target': 'new',
                'context': {
                    'default_entry_id': self.id,
                }
            }
            
    def message_handler(self, message_body):
        api_app = self.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{self.supplier_id.id}')], order='create_date desc', limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用！'))
        self.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)
                
    def approval_entry_merchant(self):
        raise UserError(_('采购方审批状态发送消息失败！'))
    
    def reject_entry_merchant(self):
        raise UserError(_('采购方审批状态发送消息失败！'))