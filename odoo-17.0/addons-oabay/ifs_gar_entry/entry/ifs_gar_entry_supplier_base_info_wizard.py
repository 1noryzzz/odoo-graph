# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecEntrySupplierBInfoWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.base.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '供应方进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.supplier'

    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)
        if 'entry_id' in defaults:
            entry = self.env[self._ref_model].browse(
                defaults.get('entry_id'))
            defaults.setdefault('business_address', entry.business_address)
            defaults.setdefault('phone', entry.phone)
            defaults.setdefault('email', entry.email)

        return defaults

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', required=True, ondelete='restrict', index=True)
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
    product_scope = fields.Text('提供的产品/服务', required=True)

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
        self.entry_id.write({
            'business_license': self.business_license,
            'phone': self.phone,
            'email': self.email,
            'business_address': self.business_address,
            'product_scope': self.product_scope,
        })

        return super().action_next()
