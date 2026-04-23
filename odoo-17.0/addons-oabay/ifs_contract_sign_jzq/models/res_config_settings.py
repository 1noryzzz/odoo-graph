# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    jzq_test_env = fields.Boolean(
        '君子签环境配置', config_parameter='ifs.contract.sign.jzq.test.env')

    jzq_service_url_test = fields.Char(
        string="服务地址", config_parameter='ifs.contract.sign.jzq.service.url.test')
    jzq_app_key_test = fields.Char(
        string="AppKey", config_parameter='ifs.contract.sign.jzq.app.key.test')
    jzq_app_secret_test = fields.Char(
        string="AppSecret", config_parameter='ifs.contract.sign.jzq.app.secret.test')

    jzq_service_url = fields.Char(
        string="服务地址", config_parameter='ifs.contract.sign.jzq.service.url')
    jzq_app_key = fields.Char(
        string="AppKey", config_parameter='ifs.contract.sign.jzq.app.key')
    jzq_app_secret = fields.Char(
        string="AppSecret", config_parameter='ifs.contract.sign.jzq.app.secret')
