# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GalaxyOpenApiLog(models.Model):
    _name = 'galaxy.open.api.log'
    _description = "openapi接口请求日志"
    
    api_app_id = fields.Many2one('galaxy.open.api.app',string="第三方应用id")
    ip = fields.Char('请求IP')
    uri = fields.Char('请求URI')
    request_data = fields.Json('请求参数')
    response_data = fields.Json('响应结果')
    is_error = fields.Boolean('是否报错',default=False)
    
    