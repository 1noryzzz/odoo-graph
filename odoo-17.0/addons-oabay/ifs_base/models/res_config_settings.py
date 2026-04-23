# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    business_registration_api_code = fields.Char(
        '工商登记信息接口代码',
        config_parameter='ifs_base.business_registration_api_code')
    business_registration_update_frequency = fields.Selection([
        ('daliy', '每天'),
        ('monthly', '每月'),
        ('quarterly', '每季度'),
        ('yearly', '每年')], string="更新频率",
        required=True, default='monthly',
        config_parameter='ifs_base.business_registration_update_frequency')
    business_reg_ocr_api_code = fields.Char(
        '营业执照识别接口代码',
        config_parameter='ifs_base.business_reg_ocr_api_code')
    verification_business_license = fields.Boolean(
        '是否验证营业执照信息', config_parameter='ifs_base.verification_business_license', default=False)

