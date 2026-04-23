# -*- coding: utf-8 -*-

import json
import logging

from functools import reduce
from odoo import _, api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GalaxyExternalApiResponseDataMixin(models.AbstractModel):
    _name = 'galaxy.external.api.response.data.mixin'
    _description = '外部API请求结果集Mixin'
    _order = 'write_date desc'

    definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='结果定义', domain=[('type', '=', 'response')], ondelete='restrict')
    json_datas = fields.Properties(
        '结果数据', definition='definition_id.params_definition')
    raw = fields.Json(
        compute='_compute_raw', inverse='_inverse_raw', string='结果源数据')

    @api.depends('json_datas')
    def _compute_raw(self):
        for record in self:
            if record.json_datas:
                record.raw = record.json_datas

    def _inverse_raw(self):
        for record in self:
            try:
                results = []
                if type(record.raw) is dict:
                    for key, value in record.raw.items():
                        results.append({
                            'name': key,
                            'value': value,
                        })
                    record.write({
                        'json_datas': results
                    })
            except:
                _logger.exception(f"parse raw result {record.raw} failed")
                
    def convert_to_json_datas(self):
        self.ensure_one()
        try:
            results = []
            if self.raw and type(self.raw) is dict:
                for key, value in self.raw.items():
                    results.append({
                        'name': key,
                        'value': value,
                    })
                    
            return results
        except:
            _logger.exception(f"parse raw result {self.raw} failed")
            


class GalaxyExternalApiResponseData(models.TransientModel):
    _name = 'galaxy.external.api.response.data'
    _inherit = ['galaxy.external.api.response.data.mixin']
    _description = '外部API请求结果集'
    _order = 'write_date desc'

    request_id = fields.Many2one(
        'galaxy.external.api.request', string='所属请求', ondelete='cascade')
    action_parser_id = fields.Many2one(
        'galaxy.external.api.action.parser', string='处理动作', ondelete='cascade')
    code = fields.Char('结果标识', index=True)

    def insert_data(self, request_id, definition_id, action_parser_id, raw_json, action):
        return self.create({
            'request_id': request_id,
            'definition_id': definition_id,
            'action_parser_id': action_parser_id,
            'code': action.get('code'),
            'raw': raw_json
        })
