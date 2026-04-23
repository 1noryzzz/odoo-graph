# -*- coding: utf-8 -*-

import json

from functools import reduce
from odoo import _, api, models, fields
from odoo.exceptions import UserError
from pypinyin import Style, lazy_pinyin


class GalaxyExternalApiResponseParser(models.Model):
    _name = 'galaxy.external.api.resp.parser'
    _description = '外部API请求结果解析器'
    _order = 'code'
    _rec_names_search = ['name', 'code']

    _sql_constraints = [
        ('code_uniq', 'unique (code)', '解析器代码已存在！'),
        ('name_uniq', 'unique (name)', '解析器名称已存在！')
    ]

    code = fields.Char(
        '解析器代码', compute='_compute_code', store=True, index=True)
    name = fields.Char('解析器名称', required=True)
    api_id = fields.Many2one(
        'galaxy.external.api', string='接口', ondelete='restrict', index=True)
    is_default = fields.Boolean('默认解析器', required=True, default=False)
    remark = fields.Html('用途说明')
    action_ids = fields.One2many(
        'galaxy.external.api.action.parser', 'parser_id', domain=[('usage', '=', 'api_parser_action')],
        context={'active_test': False}, string='处理动作')
    response_codes = fields.Json('响应代码')
    response_codes_str = fields.Char(
        compute='_compute_response_codes_str', inverse='_inverse_response_codes_str', string='响应代码', help='多个响应代码用逗号分隔')

    @api.depends('response_codes')
    def _compute_response_codes_str(self):
        for record in self:
            if record.response_codes:
                record.response_codes_str = reduce(
                    lambda x, y: x + ',' + y, record.response_codes)

    def _inverse_response_codes_str(self):
        for record in self:
            if record.response_codes_str:
                record.response_codes = record.response_codes_str.split(',')
            else:
                record.response_codes = []

    last_request_id = fields.Many2one(
        'galaxy.external.api.request', string='最后请求', ondelete='set null')
    request_ids = fields.One2many(
        'galaxy.external.api.request', 'parser_id', string='已处理的请求')

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            if record.name:
                record.code = ''.join(list(map(lambda x: x.upper(), lazy_pinyin(
                    record.name, style=Style.FIRST_LETTER))))

    def do_parse(self, **args):
        self.ensure_one()

        self.last_request_id = args.get('api_request')
        args.update({
            'request_id': self.last_request_id.id
        })

        for parse_action in self.action_ids:
            parse_action.process(**args)

        return self.last_request_id


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    usage = fields.Selection(selection_add=[
        ('api_parser_action', u'API结果解析动作'),
    ], ondelete={'api_parser_action': 'cascade'})


class GalaxyExternalApiActionParser(models.Model):
    _name = 'galaxy.external.api.action.parser'
    _inherits = {'galaxy.external.api.action': 'action_id'}
    _description = "结果处理动作"
    _order = 'sequence, write_date desc'

    parser_id = fields.Many2one(
        'galaxy.external.api.resp.parser', string='结果解析器', required=True, index=True, ondelete='cascade')
    action_id = fields.Many2one(
        'galaxy.external.api.action', required=True, ondelete='restrict', auto_join=True, index=True,
        string='执行动作', help='解析时执行的动作')
    rollback = fields.Boolean('是否回滚', default=False)
    response_definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='返回内容定义', domain=[('type', '=', 'response')], ondelete='restrict')
    last_request_id = fields.Many2one(
        'galaxy.external.api.request', string='最后请求', related='parser_id.last_request_id')

    last_data_ids = fields.One2many(
        'galaxy.external.api.response.data', 'action_parser_id', readonly=True,
        domain=lambda self: [("request_id", "=", self.last_request_id.id)], string='最近响应数据')
    sample_data = fields.Properties(
        '结果展示', definition='response_definition_id.params_definition')

    def process(self, **args):
        action = self.action_id.process(**args)
        last_data_id = False
        if type(action) is dict:
            if 'code' not in action:
                action['code'] = self.parser_id.code

            resp_data_obj = self.env['galaxy.external.api.response.data']
            if 'data' in action and type(action.get('data')) is dict:
                last_data_id = resp_data_obj.insert_data(
                    args.get(
                        'request_id'), self.response_definition_id.id,
                    self.id, action.get('data'), action)
            elif 'datas' in action and type(action.get('datas')) is list:
                for row in action.get('datas'):
                    if type(row) is dict:
                        last_data_id = resp_data_obj.insert_data(
                            args.get(
                                'request_id'), self.response_definition_id.id,
                            self.id, row, action)
        self.sample_data = last_data_id and last_data_id.json_datas

        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'parser_id' in vals:
                vals.update({
                    'usage': 'api_parser_action',
                    'api_id': self.env['galaxy.external.api.resp.parser'].browse(
                        vals.get('parser_id')).api_id.id
                })
        return super(GalaxyExternalApiActionParser, self).create(vals_list)

    def unlink(self):
        actions = self.with_context(
            force_delete=True).mapped('action_id')
        res = super().unlink()
        actions.unlink()
        return res


class GalaxyExternalApiResponseParserMixin(models.AbstractModel):
    _name = 'galaxy.external.api.resp.parser.mixin'
    _description = '结果解析器模型mixin'

    @api.model
    def do_parse(self, ori_value):
        results = []
        for key, value in ori_value.items():
            results.append({
                'name': key,
                'value': value,
            })
        return results

# class GalaxyExternalApiResult(models.Model):
#     _name = 'galaxy.external.api.result'
#     _description = '外部API调用记录'
#     _order = "create_date desc"

#     api_id = fields.Many2one(
#         'galaxy.external.api', string='接口', required=True, index=True, ondelete='cascade')
#     request_header = fields.Properties(
#         '请求头信息', definition='api_id.request_header_definition')
#     request_body = fields.Properties(
#         '请求参数', definition='api_id.request_body_definition')
#     result_raw = fields.Text('响应信息RAW')
