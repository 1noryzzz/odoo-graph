# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields


class GalaxyExternalApiAuthKV(models.Model):
    _name = 'galaxy.external.api.auth.kv'
    _inherit = ['galaxy.external.api.auth']
    _description = '私密键值对认证'

    kv_definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='键值对参数表', domain=[('type', '=', 'auth')], ondelete='restrict')
    kv_default_values = fields.Properties(
        '私密键值对默认数据', definition='kv_definition_id.params_definition')

    def do_auth(self, headers=None, query=None, body=None, rargs=None):
        super().do_auth(headers, query, body)

        headers.update({k: v for k, v in self.kv_default_values.items()})


class GalaxyExternalApi(models.Model):
    _inherit = 'galaxy.external.api'

    kv_definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='键值对参数表', readonly=False,
        domain=[('type', '=', 'auth')], compute='_compute_kv_definition_id', inverse='_inverse_kv_definition_id')
    kv_default_values = fields.Properties(
        '私密键值对默认数据', definition='kv_definition_id.params_definition', readonly=False,
        compute='_compute_kv_definition_id', inverse='_inverse_kv_default_values')

    @api.depends('request_auth')
    def _compute_kv_definition_id(self):
        for record in self:
            if record.request_auth and 'kv_definition_id' in record.request_auth._fields:
                record.kv_definition_id = record.request_auth.kv_definition_id
                record.kv_default_values = record.request_auth.kv_default_values
            else:
                record.kv_definition_id = False

    def _inverse_kv_definition_id(self):
        for record in self:
            if record.request_auth and 'kv_definition_id' in record.request_auth._fields:
                record.request_auth.kv_definition_id = record.kv_definition_id

    def _inverse_kv_default_values(self):
        for record in self:
            if record.request_auth and 'kv_default_values' in record.request_auth._fields:
                record.request_auth.kv_default_values = record.kv_default_values
