# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingBaseCompanyBusinessLicenseWizard(models.AbstractModel):
    _name = 'ifs.base.company.business.license.wizard'
    _inherit = ['galaxy.external.api.response.data.mixin', 'ifs.steps.wizard']
    _description = '营业执照添加'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
    business_license = fields.Binary(string='营业执照', required=True)

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
            else:
                self.update({
                    'definition_id': business_info.definition_id.id,
                    'raw': business_info.raw,
                    'json_datas': business_info.convert_to_json_datas(),
                })

    def action_confirm(self):
        return self.ifs_company_id.write({
            'business_license': self.business_license,
        })
