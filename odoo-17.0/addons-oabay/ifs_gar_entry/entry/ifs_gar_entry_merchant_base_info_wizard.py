# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError


class GuaranteeAccountsRecEntryMerchantBInfoWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.base.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.merchant'

    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)

        if 'entry_id' in default_fields:
            entry = self.env['ifs.gar.entry.merchant'].browse(
                defaults.get('entry_id'))
            defaults.setdefault('business_address', entry.business_address)
            defaults.setdefault('phone', entry.phone)
            defaults.setdefault('email', entry.email)

            if 'business_info_definition_id' in default_fields:
                cdetails = self.env['ifs.gar.entry.merchant.config'].retrieve_config(
                    entry.factor_id.id, entry.supplier_id.id, ['QYJYXX'])

                cdetail = cdetails.filtered(lambda c: c.code == 'QYJYXX')
                if cdetail.is_visible:
                    defaults.update({
                        'business_info_config_detail_id': cdetail.id,
                        'business_info_definition_id': cdetail.definition_id.id,
                        'business_info_is_required': cdetail.is_required,
                        'business_info_is_visible': cdetail.is_visible,
                    })

        return defaults

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='结果定义', related='entry_id.definition_id')
    json_datas = fields.Properties(
        '结果数据', definition='definition_id.params_definition', related='entry_id.json_datas')
    key_person_ids = fields.One2many(
        'ifs.base.company.detail', string='主要人员', related='entry_id.key_person_ids')

    business_license = fields.Binary(string='营业执照', required=True)
    business_date = fields.Char('执照有效期', related='entry_id.business_date')
    phone = fields.Char('电话', required=True)
    email = fields.Char('邮箱', required=True)
    business_address = fields.Char('营业地址', required=True)

    currency_id = fields.Many2one(
        'res.currency', string='Account Currency', related='entry_id.currency_id')
    is_has_company_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有车辆', default='true')
    company_vehicle_assets_value = fields.Monetary('车辆现有价值')
    is_has_company_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产', default='true')
    company_housing_assets_value = fields.Monetary('房产现有价值')
    is_has_company_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定资产', default='true')
    company_other_assets_caption = fields.Char('其他固定资产说明')
    company_other_assets_value = fields.Monetary('其他固定资产现有价值')

    business_info_config_detail_id = fields.Many2one(
        'ifs.gar.entry.merchant.config.detail', string='企业经营配置id')
    business_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='企业经营配置id')
    business_info_is_required = fields.Boolean('是否必填', default=False)
    business_info_is_visible = fields.Boolean('是否可见', default=False)
    business_info = fields.Properties(
        '企业经营相关信息', definition='business_info_definition_id.params_definition')

    def _business_license_ocr(self, reg_ocr_api_code, image):
        business_info = self.env['galaxy.external.api'].invoke(
            reg_ocr_api_code, body={'image': image.decode('utf8')}).retrieve_response('BUSINESS_INFO', False)
        if business_info and business_info.raw:
            return business_info
        else:
            raise UserError(_("营业执照识别失败，请检查营业执照是否清晰或联系管理员！"))

    @api.onchange('business_license')
    def business_license_check(self):
        if self.business_license:
            Config = self.env['ir.config_parameter'].sudo()
            is_verification = Config.get_param(
                'ifs_base.verification_business_license', False)
            reg_ocr_api_code = Config.get_param(
                'ifs_base.business_reg_ocr_api_code', 'ALY-ALYSC-YYZZXXSB')
            business_info = self._business_license_ocr(
                reg_ocr_api_code, self.business_license)
            if is_verification and (
                business_info.raw.get('name') != self.ifs_company_id.name
                    or business_info.raw.get('reg_num') != self.ifs_company_id.company_registry):

                raise UserError(_("营业执照识别信息与所填公司信息不一致，请检查营业执照是否清晰或联系管理员！"))

    def action_next(self):
        err_msgs = self.business_info_config_detail_id.validate_required(
            self.business_info)
        if len(err_msgs) > 0:
            raise ValidationError(
                _(f'请填写企业经营相关信息！包含下列内容：\n\n{"，".join(err_msgs)}'))

        self.entry_id.write({
            'business_license': self.business_license,
            'phone': self.phone,
            'email': self.email,
            'business_address': self.business_address,
            'is_has_company_vehicle_assets': self.is_has_company_vehicle_assets,
            'company_vehicle_assets_value': self.company_vehicle_assets_value,
            'is_has_company_housing_assets': self.is_has_company_housing_assets,
            'company_housing_assets_value': self.company_housing_assets_value,
            'is_has_company_other_assets': self.is_has_company_other_assets,
            'company_other_assets_caption': self.company_other_assets_caption,
            'company_other_assets_value': self.company_other_assets_value,
            'business_info_definition_id': self.business_info_definition_id.id,
            'business_info': self.business_info,
        })

        return super().action_next()
