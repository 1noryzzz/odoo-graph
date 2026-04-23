# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    risk_manage_credits_update_frequency = fields.Selection([
        ('daliy', '每天'),
        ('monthly', '每月'),
        ('quarterly', '每季度'),
        ('yearly', '每年')], string="更新频率",
        required=True, default='quarterly',
        config_parameter='ifs_base.risk_manage_credits_update_frequency')

    bairong_app_code = fields.Char(
        string="appCode", config_parameter='galaxy.bairong.app.code')

    bairong_app_key = fields.Char(
        string="appKey", config_parameter='galaxy.bairong.app.key')

    bairong_default_domain = fields.Char(
        string="访问的域名", config_parameter='galaxy.bairong.default.domain')
