# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessError, UserError
from functools import reduce
import json
import time
import base64
import requests
import datetime

def do_rpc_login(comm_var, db, login, password):
    result = comm_var.get('rpc').post(''.join([
        comm_var.get('base_url'), 'web/session/authenticate']), json={
            'db': db,
                'login': login,
                'password': password,
            'params': {
                'db': db,
                'login': login,
                'password': password,
            }
    })
    return json.loads(result.text).get('result')
EXTERNAL_API_METHOD = [
    'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE']
class GalaxyMigrateDataApi(models.TransientModel):
    _name = 'galaxy.migrate.data.api'
    _description = '数据迁移'

    code = fields.Char(
        'API调用代码', )
    name = fields.Char('API名称', )
    active = fields.Boolean('是否归档', default=True)
    state = fields.Selection([
        ('draft', '未开通'),
        ('test', '测试'),
        ('normal', '正常'),
        ('paused', '停用')
    ], string='状态', default='draft')

    base_uri = fields.Char('调用地址', required=True)
    category_id = fields.Many2one(
        'galaxy.external.api.category', string='类别', ondelete='restrict')
    platform_id = fields.Many2one(
        'res.partner', string='平台方', domain=[('is_company', '=', True)], ondelete='set null')
    vendor_id = fields.Many2one(
        'res.partner', string='供应方', domain=[('is_company', '=', True)], ondelete='set null')

    request_method = fields.Selection(
        list(map(lambda item: (item, item), EXTERNAL_API_METHOD)), string='调用方式')
    request_body_format = fields.Selection([
        ('none', '无'),
        ('form', 'Form Data'),
        ('urlencoded', 'URL Encoded'),
        ('json', 'JSON'),
        ('xml','XML'),
    ], string='请求参数格式', default='urlencoded')
    
    wizard_id = fields.Many2one('galaxy.migrate.data.api.wizard')
    
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        # db_id = self.env.context.get('db_id')
        
        # db  = self.env['galaxy.migrate.data'].browse(db_id)
        # if db.exists() and self._context.get('active_model') == 'galaxy.migrate.data':
            # self._cr.execute("truncate table {};".format(self._name.replace('.','_')))
            # comm_var={'rpc':requests.Session(),'base_url':db.url}
            # context = do_rpc_login(comm_var, db.db_name, db.username, db.password)
            # comm_var['rpc_context'] = context.get('user_context')
            # apis = db.do_rpc(comm_var, "galaxy.external.api",domain).get("records")
            # for api in apis:
            #     platform_id = False
            #     vendor_id = False
            #     if api['platform_id']:
            #         platform_id = self.env['res.partner'].sudo().search(
            #             [('name', '=', api['platform_id'][1])], limit=1)
            #         if not platform_id.exists():
            #             platform_id = self.env['res.partner'].create({
            #                 'name': api['platform_id'][1],
            #                 'is_company': True
            #             })
            #     if api['vendor_id']:
            #         vendor_id = self.env['res.partner'].sudo().search(
            #             [('name', '=', api['vendor_id'][1])], limit=1)
            #         if not vendor_id.exists():
            #             vendor_id = self.env['res.partner'].create({
            #                 'name': api['vendor_id'][1],
            #                 'is_company': True
            #             })

            #     self.create({
            #         'code':api['code'],
            #         'name':api['name'],
            #         'active':api['active'],
            #         'state':api['state'],
            #         'base_uri':api['base_uri'],
            #         'category_id':api['category_id'][0],
            #         'platform_id':platform_id.id if platform_id else False,
            #         'vendor_id':vendor_id.id if vendor_id else False,
            #         'request_method':api['request_method'],
            #         'request_body_format':api['request_body_format'],
            #     })
        
        
        res = self._search(domain, offset=offset, limit=limit, order=order, count=count)
        return res if count else self.browse(res)


class GalaxyMigrateDataApiWizard(models.TransientModel):
    _name = 'galaxy.migrate.data.api.wizard'
    _description = '数据迁移'
    
    def _default_music_update_ids(self):
        data_api_ids = self._context.get(
            'active_model') == 'galaxy.migrate.data.api' and self._context.get('active_ids') or False
        return self.env['galaxy.migrate.data.api'].browse(data_api_ids)

    api_data_ids = fields.One2many(
        'galaxy.migrate.data.api', 'wizard_id', string='音乐文件', default=_default_music_update_ids)
    
    code = fields.Char(
        'API调用代码', )
    name = fields.Char('API名称', )
    active = fields.Boolean('是否归档', default=True)
    state = fields.Selection([
        ('draft', '未开通'),
        ('test', '测试'),
        ('normal', '正常'),
        ('paused', '停用')
    ], string='状态', default='draft')
    category_id = fields.Char(string='类别')

    platform_id = fields.Char(string='平台方')
    vendor_id = fields.Char(string='供应方')
    
    def start_migrate_data(self):
        db  = self.env['galaxy.migrate.data'].browse(self.env.context.get('db_id'))
        code_list=[]
        for api_data_id in self.api_data_ids:
            code_list.append(api_data_id.code)
        db.migrate_data([('code','in',code_list)])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': '成功更新数据{}条'.format(len(code_list)),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }