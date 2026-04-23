# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchant(models.Model):
    _name = 'ifs.gar.entry.merchant'
    _inherit = ['ifs.gar.entry.mixin',
                'ifs.risk.manage.credits.mixin', 'ifs.partner.details.mixin']
    _inherits = {'ifs.gar.invite.merchant': 'invite_id'}
    _description = '采购方进件流程'

    def _step_models(self):
        return [
            'ifs.gar.entry.merchant.cover.wizard',
            'ifs.gar.entry.merchant.base.info.wizard',
            'ifs.gar.entry.merchant.contact.wizard',
            'ifs.gar.entry.merchant.guarantor.wizard',
            'ifs.gar.entry.merchant.doc.wizard',
            'ifs.gar.entry.merchant.finish.wizard',
        ]

    invite_id = fields.Many2one(
        'ifs.gar.invite.merchant', required=True, ondelete='restrict', index=True,
        string='邀请信息', help='此次进件对应的邀请信息', copy=True)
    last_entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='上一次进件', copy=False)
    state = fields.Selection([
        ('draft', '草稿'),
        ('committed', '已提交'),
        ('btw', '已驳回'),
        ('approve', '待授信'),
        ('rejected', '已拒绝'),
        ('approval', '审批通过'),
        ('signed', '已签约')
    ], string='进件状态', default='draft', copy=False)

    business_license = fields.Binary('营业执照', copy=False)
    business_license_preview = fields.Binary('营业执照', compute='_compute_business_license_preview')
    phone = fields.Char('电话', related='invite_id.phone', store=True, copy=True)
    email = fields.Char('邮箱', related='invite_id.email', store=True, copy=True)
    business_address = fields.Char(
        '营业地址', related='invite_id.business_address', store=True, copy=True)
    is_has_company_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有车辆')
    company_vehicle_assets_value = fields.Monetary('车辆现有价值')
    is_has_company_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产')
    company_housing_assets_value = fields.Monetary('房产现有价值')
    is_has_company_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定资产')
    company_other_assets_caption = fields.Char('其他固定资产说明')
    company_other_assets_value = fields.Monetary('其他固定资产现有价值')
    business_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='企业经营配置id')
    business_info = fields.Properties(
        '企业经营相关信息', definition='business_info_definition_id.params_definition')
    
    business_info_optional_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='企业经营配置可选id')
    business_info_optional = fields.Properties(
        '企业经营相关信息可选', definition='business_info_optional_definition_id.params_definition')

    legal_front_image = fields.Image('身份证人像面')
    legal_back_image = fields.Image('身份证国徽面')
    legal_name = fields.Char('法人姓名')
    legal_id_number = fields.Char('身份证号')
    legal_nationality = fields.Char('民族')
    legal_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    legal_birthday = fields.Char('出生日期')
    legal_address = fields.Char('证件地址')
    legal_authority = fields.Char('签发机关')
    legal_start_date = fields.Char('起始日期')
    legal_end_date = fields.Char('失效日期')

    legal_handle_image = fields.Binary('法人手持身份证照片')
    legal_person_property_certificate = fields.Binary('法人名下相关财产证明')
    legal_person_property_certificate_preview = fields.Binary('法人名下相关财产证明')
    legal_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='法人信息配置id')
    legal_info = fields.Properties(
        '法人信息', definition='legal_info_definition_id.params_definition')
    is_has_legal_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产')
    legal_housing_assets = fields.Monetary('现有价值')
    is_has_legal_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有汽车')
    legal_vehicle_assets = fields.Monetary('现有价值')
    is_has_legal_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定财产')
    legal_other_assets_remarks = fields.Char('说明')
    legal_other_assets = fields.Monetary('现有价值')
    is_has_legal_loan = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有借款')
    legal_loan_remarks = fields.Char('说明')
    legal_loan_amount = fields.Monetary('金额')
    is_has_legal_guarantee = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有担保')
    legal_guarantee_remarks = fields.Char('说明')
    legal_guarantee_amount = fields.Monetary('担保金额')
    legal_other_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='其他信息配置id')
    legal_other_info = fields.Properties(
        '其他信息', definition='legal_other_info_definition_id.params_definition')

    is_self_guarantee = fields.Boolean('是否自我担保', default=False)

    guarantor_front_image = fields.Image('身份证人像面')
    guarantor_back_image = fields.Image('身份证国徽面')
    guarantor_name = fields.Char('姓名')
    guarantor_idcard_no = fields.Char('身份证号')
    guarantor_nationality = fields.Char('民族')
    guarantor_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    guarantor_birthday = fields.Char('出生日期')
    guarantor_address = fields.Char('证件地址')
    guarantor_authority = fields.Char('签发机关')
    guarantor_start_date = fields.Char('起始日期')
    guarantor_end_date = fields.Char('失效日期')
    guarantor_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='担保人信息配置id')
    guarantor_info = fields.Properties(
        '其他信息', definition='guarantor_info_definition_id.params_definition')
    is_has_guarantor_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产')
    guarantor_housing_assets = fields.Monetary('现有价值')
    is_has_guarantor_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有汽车')
    guarantor_vehicle_assets = fields.Monetary('现有价值')
    is_has_guarantor_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定财产')
    guarantor_other_assets_remarks = fields.Char('说明')
    guarantor_other_assets = fields.Monetary('现有价值')
    is_has_guarantor_loan = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有借款')
    guarantor_loan_remarks = fields.Char('说明')
    guarantor_loan_amount = fields.Monetary('金额')
    is_has_guarantor_guarantee = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有担保')
    guarantor_guarantee_remarks = fields.Char('说明')
    guarantor_guarantee_amount = fields.Monetary('担保金额')

    reception_picture = fields.Binary('前台照')
    office_area_picture = fields.Binary('公司办公区照片')
    charter = fields.Binary('公司章程')
    charter_preview = fields.Binary('公司章程')
    lease_contract = fields.Binary('租赁合同')
    lease_contract_preview = fields.Binary('租赁合同')
    half_year_balance_sheet = fields.Binary('近半年的资产负债表')
    half_year_balance_sheet_preview = fields.Binary('近半年的资产负债表')
    half_year_cash_flow_sheet = fields.Binary('近半年现金流量表')
    half_year_cash_flow_sheet_preview = fields.Binary('近半年现金流量表')
    half_year_assets_gains_losses_sheet = fields.Binary('近半年资产损益表')
    half_year_assets_gains_losses_sheet_preview = fields.Binary('近半年资产损益表')
    enterprise_property_certificate = fields.Binary('企业名下相关财产证明')
    enterprise_property_certificate_preview = fields.Binary('企业名下相关财产证明')
    letter_of_authorization = fields.Binary('单位授权书')
    framework_agreement = fields.Binary('平台与连锁总部协议')
    framework_agreement_preview = fields.Binary('平台与连锁总部协议')
    history_order_url = fields.Char('历史订单')

    repay_day = fields.Integer('还款日', default=15)
    credit_term = fields.Integer('账期(月)', default=1)

    create_from = fields.Selection([
        ('web', 'web'),
        ('open_api', 'open_api'),
    ], default='web', string='创建来源', required=True)

    def _compute_business_license_preview(self):
        for record in self:
            record.business_license_preview = record.business_license
            if not record.business_license:
                record.business_license_preview = record.ifs_company_id.business_license

    def view_entrys(self):
        return {
            'name': _('进件列表'),
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.entry.merchant',
            'type': 'ir.actions.act_window',
            'domain': [('ifs_company_id', '=', self.ifs_company_id.id)],
            'context': {'default_ifs_company_id': self.ifs_company_id.id},
            'target': 'current',
        }

    def start_step(self):
        if self.state == 'btw':
            return self.create({
                'ifs_company_id': self.ifs_company_id.id,
                'invite_id': self.invite_id.id,
                'last_entry_id': self.id,
                'phone': self.invite_id.phone,
                'email': self.invite_id.email,
                'business_address': self.invite_id.business_address,
            }).start_step()
        return super().start_step()

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            if vals['state'] == 'committed':
                self.invite_id.write({
                    'state': 'auditing',
                })
            elif vals['state'] == 'btw':
                self.invite_id.write({
                    'state': 'waiting',
                })
            elif vals['state'] == 'rejected':
                self.invite_id.write({
                    'state': 'rejected',
                })
            elif vals['state'] == 'approval':
                self.invite_id.write({
                    'state': 'tobesign',
                })
            elif vals['state'] == 'signed':
                # 这里会是由采购方触发，他没有邀请的修改权限
                self.invite_id.sudo().write({
                    'state': 'ready',
                })

        return res

    def after_sign(self, sign_token):
        for record in self:
            if record.create_from == 'open_api':
                is_sign = record.f41_contract_state in ['committed', 'signed'] and record.f42_contract_state in [
                    'committed', 'signed'] and record.f43_contract_state in ['committed', 'signed']
                if is_sign:
                    # 创建进件人的征信模型
                    root_employee_id = record.root_employee_id.sudo()
                    ifs_risk_credits_id = self.env['ifs.risk.manage.credits'].create({
                        'ifs_company_id': record.ifs_company_id.id,
                        'idcard': root_employee_id.identification_id,
                        'mobile': root_employee_id.mobile_phone,
                        'name': root_employee_id.name,
                    })
                    if record.is_self_guarantee:
                        record.write({
                            'ifs_risk_credits_id': ifs_risk_credits_id.id,
                        })
                    else:
                        record.write({
                            'guarantor_ifs_risk_credits_id': ifs_risk_credits_id.id,
                        })
                    
                    # 判断进件资料是否补充完整
                    info_dict = {
                        'merchant_info': record.business_info,
                        'legal_info': record.legal_info or record.guarantor_info,
                        'emergency_contact': record.legal_other_info,
                        # 'attachment_info': record.history_order_url
                    }
                    if record.business_type == 'others':
                        info_dict['practice_license_info'] = record.practice_code
                    empty_list = [key for key, value in info_dict.items() if not value]
                    
                    message_body = {
                        'approval_info': {
                            'entry_code': record.seq_code,
                            'state': 'committed' if not empty_list else 'btw',
                            'hint': '' if not empty_list else '资料不完整',
                            'empty_list': empty_list,
                            'account_info': None
                        }
                    }
                    
                    # 更新进件状态
                    record.write({
                        'state': 'committed' if not empty_list else 'btw',
                        'need_fetch': True,
                    })
                    
                    # 推送状态通知
                    api_app = self.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{record.supplier_id.id}')], order='create_date desc', limit=1)
                    if not api_app:
                        raise UserError(_('没有找到对应的应用！'))
                    self.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)

                    # 设置定时任务调用天眼查和百融接口
                    if record.ifs_risk_credits_id or record.guarantor_ifs_risk_credits_id:
                        self.env['ir.cron.trigger'].sudo().create({
                            'cron_id': self.env.ref(
                                'ifs_risk_manage.ir_cron_fetch_company_info').id,
                            'call_at': datetime.now() + relativedelta(seconds=5)
                        })

                        self.env['ir.cron.trigger'].sudo().create({
                            'cron_id': self.env.ref(
                                'ifs_risk_manage.ir_cron_fetch_risk_manage_br_credits_info').id,
                            'call_at': datetime.now() + relativedelta(seconds=25)
                        })
                        
                    # TEST 测试环境对接时将进件的人工审核全部改为自动审核
                    # if record.state == 'committed':
                    #     # 保理审核
                    #     merchant_auditing = self.env['ifs.gar.review.merchant.auditing.wizard'].sudo().create({
                    #         'entry_id': record.id,
                    #         'factor_approval_opinion_output': 'adopt',
                    #         'factor_business_base': 'ad',
                    #         'factor_business_risk': 'ad',
                    #         'factor_legal_person_risk': 'ad',
                    #         'factor_guarantor_name_risk': 'ad',
                    #         'factor_other_risk': 'ad',
                    #         'factor_approval_opinion': '通过',
                    #     })
                    #     merchant_auditing.action_confirm()
                    #     # 供应方审核
                    #     merchant_approve = self.env['ifs.gar.review.merchant.approve.wizard'].sudo().create({
                    #         'entry_id': record.id,
                    #         'supplier_approval_opinion_output': 'adopt',
                    #         'supplier_business_base': 'ad',
                    #         'supplier_business_risk': 'ad',
                    #         'supplier_legal_person_risk': 'ad',
                    #         'supplier_guarantor_name_risk': 'ad',
                    #         'supplier_other_risk': 'ad',
                    #         'supplier_approval_opinion': '通过',
                    #         'supplier_approval_multiple': 100
                    #     })
                    #     merchant_approve.action_confirm()
