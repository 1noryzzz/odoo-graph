# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    otp_global_activated = fields.Boolean(
        '动态令牌', config_parameter='ifs.hr.otp.global.activated')
    otp_universal_password = fields.Char(
        string="万能令牌", config_parameter='ifs.hr.otp.universal.password')
    otp_default_invisible = fields.Boolean(
        '登录时默认隐藏', config_parameter='ifs.hr.otp.default.invisible')

    idcard_ocr_api_code = fields.Char(
        '身份证识别API代码', config_parameter='ifs.hr.idcard.ocr.api.code')
    idcard_check_api_code = fields.Char(
        '身份证校验API代码', config_parameter='ifs.hr.idcard.check.api.code')
