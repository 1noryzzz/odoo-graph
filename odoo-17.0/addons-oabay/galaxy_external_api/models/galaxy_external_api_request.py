# -*- coding: utf-8 -*-

from odoo import _, models, fields
from odoo.exceptions import ValidationError


class GalaxyExternalApiRequest(models.Model):
    _name = 'galaxy.external.api.request'
    _description = '外部API请求实例'
    _order = 'write_date desc'

    api_id = fields.Many2one(
        'galaxy.external.api', string='接口', required=True, index=True, ondelete='restrict')
    name = fields.Char('接口名称', related='api_id.name')
    base_uri = fields.Char('调用地址', required=True)

    request_header = fields.Json('请求头信息')
    request_params = fields.Json('Query参数')
    request_body = fields.Json('Body参数')
    request_files = fields.Json('文件参数')
    # requests 库需要的额外参数
    request_rargs = fields.Json('技术参数')
    status_code = fields.Integer('响应代码')
    response_raw = fields.Text('响应信息RAW')

    parser_id = fields.Many2one(
        'galaxy.external.api.resp.parser', string='解析器', ondelete='restrict')
    response_codes = fields.Json('响应代码', related='parser_id.response_codes')
    response_ids = fields.One2many(
        'galaxy.external.api.response.data', 'request_id', string='响应数据')

    def retrieve_response(self, code, raise_exception=True, exception_msg=_('未找到响应数据！')):
        self.ensure_one()

        resp = self.response_ids.filtered(lambda r: r.code == code)
        if raise_exception and not resp:
            raise ValidationError(exception_msg)
        return resp
