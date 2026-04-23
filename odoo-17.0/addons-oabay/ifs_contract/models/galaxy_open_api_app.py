# -*- coding: utf-8 -*-

from odoo import _, api, models, fields, http

EXTERNAL_API_METHOD = [
    'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE']

class GalaxyOpenApiApp(models.Model):
    _inherit = 'galaxy.open.api.app'
    
    authorization_callback_url = fields.Char(string='授权回调地址', required=True)
    contract_callback_url = fields.Char(string='签约回调地址', required=True)
    payment_callback_url_mini = fields.Char(string='mini-修改密码回调', required=True)
    payment_callback_url_app = fields.Char(string='app-修改密码回调', required=True)
    