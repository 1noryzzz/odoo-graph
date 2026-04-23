# -*- coding: utf-8 -*-

import base64
import io
import json
import logging
import requests
import re
import xmltodict

from functools import reduce
from odoo import _, api, models, fields
from odoo.exceptions import AccessError, UserError
from pypinyin import Style, lazy_pinyin
from urllib import parse

_logger = logging.getLogger(__name__)

EXTERNAL_API_METHOD = [
    'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE']


class GalaxyExternalApiEmbed(models.Model):
    _name = 'galaxy.external.api.embed'
    _description = '外部API的内嵌定义'

    name = fields.Char('API内嵌定义名称', required=True, index=True)
    api_id = fields.Many2one(
        'galaxy.external.api', string='接口', required=True, index=True, ondelete='restrict')
    request_body_id = fields.Many2one(
        'galaxy.external.api.definition', string='请求内容参数表', domain=[('type', '=', 'request')], ondelete='restrict')
    request_body_sample = fields.Properties(
        '请求内容信息示例', definition='request_body_id.params_definition')


class GalaxyExternalApi(models.Model):
    """
    调用时，context里可用的参数有
        active_model
        active_id
        onchange_self
    """
    _name = 'galaxy.external.api'
    _description = '外部API管理'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "code"
    _rec_names_search = ['name', 'code']

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'API调用代码已存在！'),
        ('name_uniq', 'unique (name)', 'API名称已存在！')
    ]
    code = fields.Char(
        'API调用代码', compute='_compute_code', store=True, readonly=False, required=True, index=True, help='调用此API时使用的选择代码')
    name = fields.Char('API名称', required=True, tracking=True)
    active = fields.Boolean('是否归档', default=True, tracking=True)
    state = fields.Selection([
        ('draft', '未开通'),
        ('test', '测试'),
        ('normal', '正常'),
        ('paused', '停用')
    ], string='状态', default='draft', tracking=True)
    category_id = fields.Many2one(
        'galaxy.external.api.category', string='类别', tracking=True, ondelete='restrict')
    tag_ids = fields.Many2many(
        'galaxy.external.api.tag', 'galaxy_external_api_tag_rel',
        'api_id', 'tag_id', string='接口标签')
    platform_id = fields.Many2one(
        'res.partner', string='平台方', tracking=True, domain=[('is_company', '=', True)], ondelete='set null')
    vendor_id = fields.Many2one(
        'res.partner', string='供应方', tracking=True, domain=[('is_company', '=', True)], ondelete='set null')
    effective_date = fields.Datetime('生效日期')
    expire_date = fields.Datetime('有效期至')
    description = fields.Html('API描述')

    base_uri = fields.Char('调用地址', required=True, tracking=True)
    base_test_uri = fields.Char('测试地址', tracking=True)
    request_method = fields.Selection(
        list(map(lambda item: (item, item), EXTERNAL_API_METHOD)), string='调用方式', tracking=True)
    request_header_id = fields.Many2one(
        'galaxy.external.api.definition', string='请求头参数表', domain=[('type', '=', 'request')], tracking=True, ondelete='restrict')
    request_header_sample = fields.Properties(
        '请求头信息', definition='request_header_id.params_definition')
    request_header_sample_json = fields.Json(
        '请求头信息示例', compute='_compute_request_json')
    request_query_id = fields.Many2one(
        'galaxy.external.api.definition', string='Query参数表', domain=[('type', '=', 'request')], tracking=True, ondelete='restrict')
    request_query_sample = fields.Properties(
        'Query', definition='request_query_id.params_definition')
    request_query_sample_json = fields.Json(
        'Query示例', compute='_compute_request_json')
    request_body_format = fields.Selection([
        ('none', '无'),
        ('form', 'Form Data'),
        ('urlencoded', 'URL Encoded'),
        ('json', 'JSON'),
        ('xml', 'XML'),
    ], string='请求参数格式', default='urlencoded')
    request_body_id = fields.Many2one(
        'galaxy.external.api.definition', string='请求内容参数表', domain=[('type', '=', 'request')], tracking=True, ondelete='restrict')
    request_body_sample = fields.Properties(
        '请求内容信息', definition='request_body_id.params_definition')
    request_body_embed_ids = fields.One2many(
        'galaxy.external.api.embed', 'api_id', string='内嵌定义', tracking=True)
    request_body_sample_json = fields.Json(
        '请求内容信息示例', compute='_compute_request_json')
    request_files_id = fields.Many2one(
        'galaxy.external.api.definition', string='文件参数表', domain=[('type', '=', 'file')], tracking=True, ondelete='restrict')
    request_files_sample = fields.Properties(
        '文件参数', definition='request_files_id.params_definition')
    request_files_sample_json = fields.Json(
        '文件参数示例', compute='_compute_request_json')
    request_rargs_id = fields.Many2one(
        'galaxy.external.api.definition', string='技术参数表', domain=[('type', '=', 'tech')], tracking=True, ondelete='restrict')
    request_rargs_sample = fields.Properties(
        '技术参数', definition='request_rargs_id.params_definition')
    request_rargs_sample_json = fields.Json(
        '技术参数示例', compute='_compute_request_json')

    attachment_ids = fields.One2many(
        'galaxy.external.api.attachment', 'api_id', context={'active_test': False}, string='附加文件')

    request_auth = fields.Reference(selection=[
        ('galaxy.external.api.auth.kv', '基本认证'),
        ('galaxy.external.api.auth.token', '令牌认证'),
        ('galaxy.external.api.auth.oauth', 'OAuth')
    ], string='认证方式')
    auth_model_name = fields.Char(
        compute='_compute_auth_model_name', string='认证数据模型')

    pre_action_ids = fields.One2many(
        'galaxy.external.api.action', 'api_id', domain=[('usage', '=', 'api_pre_action')],
        context={'active_test': False}, string='预执行动作', tracking=True)
    post_action_ids = fields.One2many(
        'galaxy.external.api.action', 'api_id', domain=[('usage', '=', 'api_post_action')],
        context={'active_test': False}, string='后执行动作', tracking=True)

    response_raw = fields.Text(string='结果源数据')
    response_parser_ids = fields.One2many(
        'galaxy.external.api.resp.parser', 'api_id', string='结果解析器', tracking=True)

    request_ids = fields.One2many(
        'galaxy.external.api.request', 'api_id', string='调用日志')
    invoke_count = fields.Char(
        compute='_compute_invoke_count', string='累计调用')

    def _generate_many2x_body(self, record, field_name):
        m2x_body = {}
        if field_name in record._fields:
            field_type = record._fields[field_name].type
            if field_type == 'properties':
                definition = record._fields[field_name].definition
                definition_many2x = record[definition.split('.')[0]]
                params_definition = definition_many2x[definition.split('.')[1]]
                m2x_body = reduce(
                    self._generate_embed, params_definition, record[field_name])
            elif field_type == 'binary' and record[field_name]:
                m2x_body = record[field_name].decode('utf-8')
            else:
                m2x_body = record[field_name]
        else:
            m2x_body = record.name_get()[0][1]

        return m2x_body

    def _generate_many2x_file(self, record, field_name, ct_type):
        if ct_type == 'file_desc':
            return '二进制数据'

        if field_name in record._fields and record._fields[field_name].type == 'binary':
            io_file = io.BytesIO(base64.b64decode(record[field_name]))
            io_file.name = record.name_get()[0][1]
            return io_file

        return io.BytesIO()

    def _generate_embed(self, prev, curr, ct_type='body'):
        if not prev.get(curr.get('name')):
                return prev
        if curr.get('type') == 'many2one':
            m2o_record = self.env[curr.get('comodel')].browse( prev.get(curr.get('name')))
                # curr.get('value', 0))
            if m2o_record.exists():
                prev.update({
                    curr.get('name'): self._generate_many2x_body(m2o_record, curr.get('field'))
                    if ct_type == 'body' else self._generate_many2x_file(m2o_record, curr.get('field'), ct_type)
                })
        elif curr.get('type') == 'many2many':
            m2o_records = self.env[curr.get('comodel')].browse(
                prev.get(curr.get('name')))
            inner_list = []
            for m2o_record in m2o_records:
                inner_list.append(
                    self._generate_many2x_body(m2o_record, curr.get('field'))
                    if ct_type == 'body' else self._generate_many2x_file(m2o_record, curr.get('field'), ct_type))

            prev.update({curr.get('name'): inner_list})
        # else:
        #     prev.update({curr.get('name'): curr.get('value')})
        return prev

    def _generate_files(self, prev, curr):
        return self._generate_embed(prev, curr, 'file')

    def _generate_files_desc(self, prev, curr):
        return self._generate_embed(prev, curr, 'file_desc')

    def _append_usage(self, vals):
        if 'pre_action_ids' in vals:
            vals['pre_action_ids'] = list(map(
                lambda row: [0, row[1], {
                    **row[2],
                    'usage': 'api_pre_action'
                }] if row[0] == 0 else row, vals.get('pre_action_ids', [])))
        if 'post_action_ids' in vals:
            vals['post_action_ids'] = list(map(
                lambda row: [0, row[1], {
                    **row[2],
                    'usage': 'api_post_action'
                }] if row[0] == 0 else row, vals.get('post_action_ids', [])))

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            if record.name and not record.code:
                record.code = ''.join(list(map(lambda x: x.upper(), lazy_pinyin(
                    record.name, style=Style.FIRST_LETTER))))

    @api.depends('request_auth')
    def _compute_auth_model_name(self):
        for record in self:
            if record.request_auth:
                record.auth_model_name = record.request_auth._name
            else:
                record.auth_model_name = False

    @api.depends('request_ids')
    def _compute_invoke_count(self):
        for record in self:
            record.invoke_count = 0
            if record.request_ids:
                record.invoke_count = len(record.request_ids.ids)

    @api.depends('request_header_sample', 'request_query_sample', 'request_body_sample', 'request_files_sample', 'request_rargs_sample')
    def _compute_request_json(self):
        for record in self:
            request_json = {
                'request_header_sample_json': '',
                'request_query_sample_json': '',
                'request_body_sample_json': '',
                'request_files_sample_json': '',
                'request_rargs_sample_json': '',
            }
            if record.request_header_sample:
                request_json['request_header_sample_json'] = record.request_header_sample
                # request_json.update({
                #     'request_header_sample_json': reduce(lambda prev, curr: {
                #         **prev, curr.get('name'): curr.get('value')
                #     }, record.request_header_sample, {})
                # })
            if record.request_query_sample:
                request_json['request_query_sample_json'] = record.request_query_sample
                # request_json.update({
                #     'request_query_sample_json': reduce(lambda prev, curr: {
                #         **prev, curr.get('name'): curr.get('value')
                #     }, record.request_query_sample, {})
                # })
            if record.request_body_sample:
                request_json['request_body_sample_json'] = reduce(record._generate_embed, record.request_body_id.params_definition, record.request_body_sample)
                # request_json.update({
                #     'request_body_sample_json': reduce(
                #         record._generate_embed, record.request_body_sample, {})
                # })
            if record.request_files_sample:
                request_json.update({
                    'request_files_sample_json': reduce(record._generate_files_desc, record.request_files_id.params_definition,record.request_files_sample)
                })
            if record.request_rargs_sample:
                request_json['request_rargs_sample_json'] = record.request_rargs_sample
                # request_json.update({
                #     'request_rargs_sample_json': reduce(lambda prev, curr: {
                #         **prev, curr.get('name'): curr.get('value')
                #     }, record.request_rargs_sample, {})
                # })
            record.update(request_json)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._append_usage(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._append_usage(vals)
        return super().write(vals)

    def _invoke(self, **args):
        self.ensure_one()

        headers = args.get('headers', {})
        query = args.get('query', {})
        body = args.get('body', {})
        files = args.get('files', {})
        rargs = args.get('rargs', {})

        request_base_uri = self.base_test_uri or self.base_uri
        if self.state == 'normal':
            request_base_uri = self.base_uri
            
        for k,v in query.items():
            k1 = '{' + k + '}'
            if request_base_uri.count(k1) > 0:
                request_base_uri = request_base_uri.replace(k1,v)
            
        if self.request_body_format == 'form':
            headers.update({
                'Content-Type': 'multipart/form-data'
            })
        elif self.request_body_format == 'urlencoded':
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
            })
            body = parse.urlencode(body)
        elif self.request_body_format == 'xml':
            headers.update({
                'Content-Type': 'application/xml'
            })    
        try:
            session = None
            if self.request_auth:
                session = self.request_auth.do_auth(
                    headers, query, body, rargs)

            if not session:
                session = requests.session()

            for pre_action in self.pre_action_ids:
                # 这里暂时没有记录下每次处理的过程值
                pre_action.process(
                    headers=headers, query=query, body=body, files=files, rargs=rargs)

            if self.request_body_format == 'json':
                response = session.post(
                    request_base_uri, headers=headers, params=query, json=body, files=files, **rargs)
            elif self.request_body_format == 'xml':
                body = xmltodict.unparse(body, pretty=False, full_document=False)
                response = session.post(
                    request_base_uri, headers=headers, params=query, data=body.encode('UTF-8'), files=files, **rargs) 
                if response.text.index('?>') > 0:
                    xml_header = response.text[0:response.text.index("?>")+2]
                    encoding_match = re.search(r'encoding="(.*?)"', xml_header)
                    if encoding_match:
                        encoding = encoding_match.group(1)
                        response.encoding = encoding
            else:
                # if self.code == 'UMS-AGREEMENT_SIGN':
                #     print("{}?accesser_id={}&sign_data={}&json_data={}".format(request_base_uri, query.get(
                #         "accesser_id"), query.get("sign_data"), query.get("json_data")))
                #     raise UserError("{}?accesser_id={}&sign_data={}&json_data={}".format(
                #         request_base_uri, query.get("accesser_id"), query.get("sign_data"), query.get("json_data")))
                if self.request_method == 'GET':
                    response = session.get(
                        request_base_uri, headers=headers, params=query, **rargs)
                else:
                    response = session.post(
                        request_base_uri, headers=headers, params=query, data=body, files=files, **rargs)

            default_parser = False
            if self.response_parser_ids:
                default_parser = (self.response_parser_ids.filtered(
                    'is_default') or self.response_parser_ids)[0]

            api_request = self.env['galaxy.external.api.request'].create({
                'api_id': self.id,
                'base_uri': request_base_uri,
                'request_header': headers,
                'request_params': query,
                'request_body': body,
                'request_files': reduce(lambda prev, curr: {
                    **prev, curr[0]: '二进制文件'
                }, files.items(), {}),
                'request_rargs': rargs,
                'status_code': response.status_code,
                'response_raw': response.text,
                'parser_id': default_parser.id if default_parser else False,
            })

            last_result = {}
            for post_action in self.post_action_ids:
                # 这里暂时没有记录下每次处理的过程值
                post_action.process(
                    headers=headers, query=query, body=body, response=response, last_result=last_result, api_request=api_request)

            # with self.env.cr.savepoint():
            if default_parser and default_parser.exists():
                default_parser.do_parse(
                    headers=headers, query=query, body=body, response=response, last_result=last_result, api_request=api_request)

            return api_request
        except UserError as e:
            raise e
        except Exception as e:
            _logger.error(repr(e))
            raise AccessError(_('测试接口时发生错误'))

    @api.model
    def invoke(self, code, **args):
        ExternalApiReq = self.env['galaxy.external.api.request']
        ExternalApiRspData = self.env['galaxy.external.api.response.data']
        parser_id = False
        with self.pool.cursor() as cr:
            self.env.flush_all()
            cr._cnx.autocommit = True
            ExternalApi = self.with_env(self.env(cr=cr))

            ext_api = ExternalApi.search(
                [('code', '=', code)], limit=1)
            if not (ext_api.exists() and (args.get('is_test', False) or ext_api.state == 'normal')):
                raise AccessError('接口不存在或已停用')

            api_request = ext_api._invoke(**args)
            response_ids = api_request.response_ids
            parser_id = api_request.parser_id.id

            for response_data in api_request.response_ids:
                rsp_data = ExternalApiRspData.browse(response_data.id)
                for field_name, field in ExternalApiRspData._fields.items():
                    if field_name != 'definition_id':
                        self.env.cache.set(
                            rsp_data, field, response_data[field_name])
                    else:
                        self.env.cache.set(
                            rsp_data, field, response_data.definition_id.id)

        api_request = ExternalApiReq.browse(api_request.id)
        self.env.cache.set(
            api_request, ExternalApiReq._fields['parser_id'], parser_id)
        self.env.cache.set(
            api_request, ExternalApiReq._fields['response_ids'], response_ids.ids)
        return api_request

    def invoke_test(self):
        self.ensure_one()

        try:
            headers = {}
            query = {}
            body = {}
            files = {}
            rargs = {}
            if self.request_header_sample:
                headers = self.request_header_sample
            if self.request_query_sample:
                query = self.request_query_sample
            if self.request_body_sample:
                # request_body_id.params_definition
                # body = self.request_body_sample
                body = reduce(
                    self._generate_embed, self.request_body_id.params_definition, self.request_body_sample)
            if self.request_files_sample:
                files = reduce(
                    self._generate_files, self.request_files_id.params_definition,self.request_files_sample)
            # requests 库的额外参数
            if self.request_rargs_sample:
                rargs = self.request_rargs_sample
                # rargs = reduce(lambda prev, curr: {
                #     **prev, curr.get('name'): curr.get('value')
                # }, self.request_rargs_sample, {})

            api_request = self._invoke(
                headers=headers, query=query, body=body, files=files, rargs=rargs)
            self.response_raw = api_request.response_raw
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'sticky': False,
                    'message': _(f'测试成功，状态码：{api_request.status_code}'),
                    # 增加一个window_close，可以让当前页面刷新
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except UserError as e:
            raise e
        except Exception as e:
            _logger.error(repr(e))
            raise AccessError(_('构造请求参数时发生错误'))
