# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GalaxyExternalApiAuthToken(models.Model):
    _name = 'galaxy.external.api.auth.token'
    _inherit = ['galaxy.external.api.auth']
    _description = '令牌认证'

    token_type = fields.Selection([
        ('bearer', 'Bearer Token'),
        ('other', '其它')
    ], string='令牌类型', default='bearer')
    token = fields.Text('令牌')

    def do_auth(self, headers=None, query=None, body=None, rargs=None):
        super().do_auth(headers, query, body)

        token_type = 'Bearer' if self.token_type == 'bearer' else ''
        headers.update({
            'Authorization': f'{token_type} {self.token}'
        })


class GalaxyExternalApi(models.Model):
    _inherit = 'galaxy.external.api'

    token_type = fields.Selection([
        ('bearer', 'Bearer Token'),
        ('other', '其它')
    ], string='令牌类型', compute='_compute_auth_token', inverse='_inverse_token_type')
    token = fields.Text(
        '令牌', compute='_compute_auth_token', inverse='_inverse_auth_token')

    @api.depends('request_auth')
    def _compute_auth_token(self):
        for record in self:
            if record.request_auth and 'token_type' in record.request_auth._fields:
                record.token_type = record.request_auth.token_type
                record.token = record.request_auth.token

    def _inverse_token_type(self):
        for record in self:
            if record.request_auth and 'token_type' in record.request_auth._fields:
                record.request_auth.token_type = record.token_type

    def _inverse_auth_token(self):
        for record in self:
            if record.request_auth and 'token' in record.request_auth._fields:
                record.request_auth.token = record.token
