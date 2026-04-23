# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GalaxyExternalApiDefinition(models.Model):
    _name = 'galaxy.external.api.definition'
    _description = '外部API参数表'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', '参数表名称已存在！')
    ]

    name = fields.Char('参数表名称', required=True, index=True)
    type = fields.Selection([
        ('request', '请求参数'),
        ('tech', '技术参数'),
        ('auth', '认证参数'),
        ('file', '文件参数'),
        ('response', '响应参数'),
    ], string='参数表类型', required=True)
    params_definition = fields.PropertiesDefinition('参数配置')


class GalaxyExternalApiAuthMixin(models.AbstractModel):
    _name = 'galaxy.external.api.auth'
    _description = '认证方式mixin'

    name = fields.Char('认证方式名')

    def do_auth(self, headers=None, query=None, body=None, rargs=None):
        self.ensure_one()


class GalaxyExternalApiAuthOAuth(models.Model):
    _name = 'galaxy.external.api.auth.oauth'
    _inherit = ['galaxy.external.api.auth']
    _description = 'OAuth认证'
