# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessError, UserError
# from odoo.exceptions import Warning
from functools import reduce
import json
import time
import base64
import requests
import datetime
from ..tools import rpc,migrate_data17
from odoo.http import request

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

api_columns=["id","category_id","platform_id","vendor_id","request_header_id","request_query_id","request_body_id","request_files_id","request_rargs_id","code","name","state","base_uri","base_test_uri","request_method","request_body_format","request_auth","request_header_sample","request_query_sample","request_body_sample","request_files_sample","request_rargs_sample","description","response_raw","active","effective_date","expire_date","request_body_embed_ids","attachment_ids","pre_action_ids","post_action_ids","response_parser_ids"]
api_action_columns=["id","api_id","ir_actions_server_id","sequence","action_name","rollback","active"]
api_action_parser_columns=["id","parser_id","action_id","response_definition_id","sample_data","rollback"]
api_attachment_columns=["id","api_id","name","attachment"]
api_auth_kv_columns=["id","kv_definition_id","name","kv_default_values"]
api_auth_token_columns=["id","name","token","token_ype"]
api_auth_ums_ak_columns=["id","expires_in","name","ums_ak_uri","access_token","err_code","err_info"]
api_auth_bairong_ak_columns=["id","name"]
api_auth_oauth_columns=["id","name"]
api_auth_ums_body_sig_columns=["id","name"]
api_auth_jzq_columns=["id","name"]
api_category_columns=["id","sequence","code","name","remark"]
api_definition_columns=["id","name","type","params_definition"]
api_request_columns=["id","api_id","status_code","parser_id","base_uri","request_header","request_params","request_body","request_files","request_rargs","response_raw"]
api_resp_parser_columns=["id","api_id","code","name","remark","is_default","action_ids","response_codes"]
api_response_data_columns=["id","request_id","action_parser_id","definition_id","code","json_datas"]
api_embed_columns=["id","name","request_body_id","api_id","request_body_sample"]
ir_act_server_columns=["id","type","binding_type","binding_view_types","name","sequence","model_id","usage","state","model_name","code","activity_date_deadline_range","activity_date_deadline_range_type","mail_post_autofollow","website_published"]
model_fields={
    "galaxy.external.api":api_columns,
    "galaxy.external.api.action":api_action_columns,
    "galaxy.external.api.action.parser":api_action_parser_columns,
    "galaxy.external.api.attachment":api_attachment_columns,
    "galaxy.external.api.auth.kv":api_auth_kv_columns,
    "galaxy.external.api.auth.token":api_auth_token_columns,
    "galaxy.external.api.ums.ak":api_auth_ums_ak_columns,
    "galaxy.external.api.auth.bairong.ak":api_auth_bairong_ak_columns,
    "galaxy.external.api.auth.oauth":api_auth_oauth_columns,
    "galaxy.external.api.auth.ums.body.sig":api_auth_ums_body_sig_columns,
    "galaxy.external.api.auth.jzq":api_auth_jzq_columns,
    "galaxy.external.api.category":api_category_columns,
    "galaxy.external.api.definition":api_definition_columns,
    "galaxy.external.api.request":api_request_columns,
    "galaxy.external.api.resp.parser":api_resp_parser_columns,
    "galaxy.external.api.response.data":api_response_data_columns,
    "galaxy.external.api.embed":api_embed_columns,
    "ir.actions.server":ir_act_server_columns
}
def get_model_fields(model_name):
    model = request.env[model_name]
    fields = {}
    field_types = {}
    for field_name, field_info in model.fields_get().items():
        if field_name == 'code':
            pass
        if field_info.get('type') == 'binary' or (model._fields[field_name].compute and not field_info.get('store')) or field_name in ['create_uid','write_uid','message_follower_ids','message_ids','website_message_ids','activity_ids']:
            continue
        field_types[field_name] = field_info.get('type')
        if field_info.get('type') == 'many2one':
            fields[field_name] = {
                    'fields':{
                        'id':{},
                        'name':{}
                    }
                }
        elif field_info.get('type') == 'one2many' or field_info.get('type') == 'many2many':
            fields[field_name] = {'fields':{
                'id':{}
            }}
        else:
            fields[field_name] = {}
    return fields,field_types


class GalaxyExternalApiEmbed(models.Model):
    _name = 'galaxy.migrate.data'
    _description = '数据迁移'

    name = fields.Char('名称', required=True)

    url = fields.Char('URL', required=True, index=True)
    db_name = fields.Char('数据库名称', required=True, index=True)
    username = fields.Char('用户名', required=True, index=True)
    password = fields.Char('密码', required=True, index=True)
    version = fields.Selection(selection=[('16.0','16.0'),('17.0','17.0')],required=True,default='16.0')
    
    
    def do_rpc_login(self,comm_var):
        result = requests.post(''.join([
            self.url, '/web/session/authenticate']), json={
                'db': self.db_name,
                    'login': self.username,
                    'password': self.password,
                'params': {
                    'db': self.db_name,
                    'login': self.username,
                    'password': self.password,
                }
        })
        for cookie in result.cookies:
            if cookie.name == 'session_id':
                comm_var['session_id'] = cookie.value
        return json.loads(result.text).get('result')

    def do_rpc17(self,comm_var, model,fields,domain=[],limit=800,offset=0,order="id ASC",timeout=(300,300)):
        if not comm_var.get('session_id'):
            login_result = requests.post(''.join([
                self.url, '/web/session/authenticate']), json={
                    'db': self.db_name,
                        'login': self.username,
                        'password': self.password,
                    'params': {
                        'db': self.db_name,
                        'login': self.username,
                        'password': self.password,
                    }
            })
            for cookie in login_result.cookies:
                if cookie.name == 'session_id':
                    comm_var['session_id'] = cookie.value
                    print('登录成功')
        fields,field_types = get_model_fields(model)
        session_id = comm_var.get('session_id')
        with  requests.post(f"{self.url}/web/dataset/call_kw/{model}/web_search_read",
            headers={"X-Openerp-Session-Id":comm_var.get('session_id'),
                     'cookie':f'frontend_lang=zh_CN; tz=Etc/GMT-8; cids=1; session_id={session_id}'
                     },timeout=timeout,
            json={
                "id": 19,
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": model,
                    "method": "web_search_read",
                    "args": [],
                    "kwargs": {
                        "domain": domain,
                        "specification": fields,
                        "limit":limit,
                        "offset":offset,
                        "order":order
                    }
                }
            }) as response:
            content = b""
            for chunk in response.iter_content(chunk_size=64):
                content += chunk
            result_text = content.decode('utf-8')
        result = json.loads(result_text).get('result')
        for record in result.get('records'):
            for k,v in record.items():
                if v and field_types[k] == 'many2one':
                    record[k] = [v.get('id'),v.get('name')]
                elif v and field_types[k] in ['one2many','many2many']:
                    record[k] = sorted([item['id'] for item in v])
        return result

    def do_rpc(self, comm_var, model,domain):
        if self.version == '17.0':
            return self.do_rpc17(comm_var=comm_var,model=model,fields=model_fields.get(model),domain=domain)
        comm_var['base_url'] = self.url
        if comm_var.get('rpc') == None:
            session = requests.Session()

            comm_var['rpc'] = session
            context = do_rpc_login(
                comm_var, self.db_name, self.username, self.password)
            comm_var['rpc_context'] = context.get('user_context')
        result = comm_var.get('rpc').post(
            ''.join([comm_var.get('base_url'), 'web/dataset/', 'search_read']),
            json={
                'id': int(time.time()),
                'jsonrpc': '2.0',
                'method': 'call',
                
                'params': {
                    "model": model,
                    "fields":model_fields.get(model),
                    "domain":domain
                },
            })
        data = json.loads(result.text).get('result')
        if model == 'galaxy.external.api.definition':
            for record in data.get('records'):
                params_definitions = record.get('params_definition')
                for params_definition in params_definitions:
                    if 'view_in_kanban' in params_definition:
                        params_definition['view_in_cards'] = params_definition['view_in_kanban']
                        params_definition.pop('view_in_kanban')
        return data

    def start_migrate(self):
        self._cr.execute("truncate table {};".format('galaxy.migrate.data.api'.replace('.','_')))
        db = self
        comm_var = {}
        if self.version == '16.0':
            comm_var={'rpc':requests.Session(),'base_url':db.url}
            context = do_rpc_login(comm_var, db.db_name, db.username, db.password)
            comm_var['rpc_context'] = context.get('user_context')

        apis = db.do_rpc(comm_var, "galaxy.external.api",domain=[]).get("records")
        for api in apis:
            platform_id = False
            vendor_id = False
            if api['platform_id']:
                platform_id = self.env['res.partner'].sudo().search(
                    [('name', '=', api['platform_id'][1])], limit=1)
                if not platform_id.exists():
                    platform_id = self.env['res.partner'].create({
                        'name': api['platform_id'][1],
                        'is_company': True
                    })
            if api['vendor_id']:
                vendor_id = self.env['res.partner'].sudo().search(
                    [('name', '=', api['vendor_id'][1])], limit=1)
                if not vendor_id.exists():
                    vendor_id = self.env['res.partner'].create({
                        'name': api['vendor_id'][1],
                        'is_company': True
                    })
            self.env['galaxy.migrate.data.api'].sudo().create({
                'code':api['code'],
                'name':api['name'],
                'active':api['active'],
                'state':api['state'],
                'base_uri':api['base_uri'],
                'category_id':api['category_id'][0],
                'platform_id':platform_id.id if platform_id else False,
                'vendor_id':vendor_id.id if vendor_id else False,
                'request_method':api['request_method'],
                'request_body_format':api['request_body_format'],
            })
        return {
            'name': _('接口列表'),
            'view_mode': 'tree',
            'res_model': 'galaxy.migrate.data.api',
            'type': 'ir.actions.act_window',
            'context': {'db_id':db.id,'search_default_group_platform_id':True},
            'domain': [],
            'target': 'current',
           
        }
    def migrate_data(self,domain=[]):
        comm_var={'rpc':requests.Session(),'base_url':self.url}
        context = do_rpc_login(comm_var, self.db_name, self.username, self.password)
        comm_var['rpc_context'] = context.get('user_context')
        api_dummy=self.env['ir.model'].search([('model','=','galaxy.external.api.dummy')])
        apis = self.do_rpc(comm_var, "galaxy.external.api",domain).get("records")
        for api in apis:
            api_id = self.env['galaxy.external.api'].search([('code','=',api['code'])])
            if api_id.exists():
                self.api_update(api_id,api,comm_var)
                continue
            print(api['name'])

            
            platform_id=False
            vendor_id=False
            if api['platform_id']:
                platform = self.env['res.partner'].search([('name','=',api['platform_id'][1])])
                if not platform.exists():
                    platform=self.env['res.partner'].create({
                        'name':api['platform_id'][1],
                        'is_company':True
                    })
                platform_id = platform.id
            if api['vendor_id']:
                vendor = self.env['res.partner'].search([('name','=',api['vendor_id'][1])])
                if not vendor.exists():
                    vendor=self.env['res.partner'].create({
                        'name':api['vendor_id'][1],
                        'is_company':True
                    })
                vendor_id = vendor.id
            api_id = self.env['galaxy.external.api'].create({
                'category_id':api['category_id'][0],
                'platform_id':platform_id,
                'vendor_id':vendor_id,
                # 'effective_date':datetime.datetime.now(),
                # 'expire_date':datetime.datetime.now(),
                'code':api['code'],
                'name':api['name'],
                'state':api['state'],
                'base_uri':api['base_uri'],
                'base_test_uri':api['base_test_uri'],
                'request_method':api['request_method'],
                'request_body_format':api['request_body_format'],
                # 'request_auth':auth_id,
                'request_header_sample':api['request_header_sample'],
                'request_query_sample':api['request_query_sample'],
                'request_body_sample':api['request_body_sample'],
                'request_files_sample':api['request_files_sample'],
                'request_rargs_sample':api['request_rargs_sample'],
                'description':api['description'],
                'response_raw':api['response_raw'],
                'active':api['active']
            })

            request_header_id=False
            request_query_id=False
            request_body_id=False
            request_files_id=False
            request_rargs_id=False
            auth_id=False
            if api['request_auth']:
                request_auth = self.do_rpc(comm_var,api['request_auth'].split(',')[0],[('id','=',api['request_auth'].split(',')[1])]).get('records')[0]
                request_auth_id = self.env[api['request_auth'].split(',')[0]].search([('name','=',request_auth['name'])])
                if not request_auth_id.exists():
                    request_auth_id=self.env[api['request_auth'].split(',')[0]].create({
                        'name':request_auth['name']
                    })
                    if api['request_auth'].split(',')[0] == "galaxy.external.api.auth.kv":
                        kv_definition=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",request_auth['kv_definition_id'][0])]).get("records")[0]
                        kv_definition_id = self.env['galaxy.external.api.definition'].search([('name','=',kv_definition['name'])])
                        if not kv_definition_id.exists():
                            kv_definition_id=self.env['galaxy.external.api.definition'].create(kv_definition)
                        
                        request_auth_id.write({
                            'kv_default_values':request_auth['kv_default_values'],
                            'kv_definition_id':kv_definition_id.id
                        })
                auth_id="{},{}".format(api['request_auth'].split(',')[0],request_auth_id.id)
            
            if api['request_header_id']:
                request_header=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_header_id'][0])]).get("records")[0]
                request_header_id = self.env['galaxy.external.api.definition'].search([('name','=',request_header['name'])])
                if not request_header_id.exists():
                    request_header_id=self.env['galaxy.external.api.definition'].sudo().create(request_header).id
            if api['request_query_id']:
                request_query=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_query_id'][0])]).get("records")[0]
                request_query_id = self.env['galaxy.external.api.definition'].search([('name','=',request_query['name'])])
                if not request_query_id.exists():
                    request_query_id=self.env['galaxy.external.api.definition'].sudo().create(request_query).id
            if api['request_body_id']:
                request_body=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_body_id'][0])]).get("records")[0]
                request_body_id = self.env['galaxy.external.api.definition'].search([('name','=',request_body['name'])])
                if not request_body_id.exists():
                    request_body_id=self.env['galaxy.external.api.definition'].sudo().create(request_body).id
            if api['request_files_id']:
                request_files=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_files_id'][0])]).get("records")[0]
                request_files_id = self.env['galaxy.external.api.definition'].search([('name','=',request_files['name'])])
                if not request_files_id.exists():
                    request_files_id=self.env['galaxy.external.api.definition'].sudo().create(request_files).id
            if api['request_rargs_id']:
                request_rargs=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_rargs_id'][0])]).get("records")[0]
                request_rargs_id = self.env['galaxy.external.api.definition'].search([('name','=',request_rargs['name'])])
                if not request_rargs_id.exists():
                    request_rargs_id=self.env['galaxy.external.api.definition'].sudo().create(request_rargs).id
            api_id.write({
                'request_header_id':request_header_id,
                'request_query_id':request_query_id,
                'request_body_id':request_body_id,
                'request_files_id':request_files_id,
                'request_rargs_id':request_rargs_id,
                'request_auth':auth_id
            })
            if api['request_body_embed_ids']:
                request_body_embed_ids=[]
                for id in api['request_body_embed_ids']:
                    embed = self.do_rpc(comm_var, "galaxy.external.api.embed",[("id","=",id)]).get("records")[0]
                    embed_request_body=self.do_rpc(comm_var,'galaxy.external.api.definition',[('id','=',embed['request_body_id'][0])]).get("records")[0]
                    embed_request_body_id = self.env['galaxy.external.api.definition'].search([('name','=',embed_request_body['name'])])
                    # if not embed_request_body_id.exists():
                        
                    # else:
                    #     embed_request_body_id.unlink()
                    if embed_request_body_id.exists():
                        embed_request_body.pop('id')
                        embed_request_body_id.write(embed_request_body)
                        # embed_request_body_id.unlink()
                    else:
                        embed_request_body_id=self.env['galaxy.external.api.definition'].create(embed_request_body)
                    embed['request_body_id']=embed_request_body_id.id
                    embed['api_id']=api_id.id
                    embed_id=self.env['galaxy.external.api.embed'].create(embed)
                    request_body_embed_ids.append(embed_id.id)
                api_id.write({
                    'request_body_embed_ids':[fields.Command.set(request_body_embed_ids)]
                })
            if api['attachment_ids']:
                attachment_ids=[]
                for id in api['attachment_ids']:
                    attachment = self.do_rpc(comm_var, "galaxy.external.api.attachment",[("id","=",id)]).get("records")[0]
                    attachment['api_id']=api_id.id
                    attachment_id=self.env['galaxy.external.api.attachment'].create(attachment)
                    attachment_ids.append(attachment_id.id)
                api_id.write({
                    'attachment_ids':[fields.Command.set(attachment_ids)]
                })
            if api['pre_action_ids']:
                pre_action_ids=[]
                for id in api['pre_action_ids']:
                    pre_action = self.do_rpc(comm_var, "galaxy.external.api.action",[("id","=",id)]).get("records")
                    if len(pre_action)==0:
                        continue
                    else:
                        pre_action=pre_action[0]
                    pre_action['api_id']=api_id.id
                    ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",pre_action['ir_actions_server_id'][0])]).get("records")[0]
                    ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                    ir_actions_server_id = self.env['ir.actions.server'].sudo().search([('name','=',ir_actions_server['name'])])
                    if not ir_actions_server_id.exists():   
                        ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                    else:
                        ir_actions_server.pop('id')
                        ir_actions_server_id.write(ir_actions_server)
                    pre_action['ir_actions_server_id']=ir_actions_server_id.id
                    pre_action_id = self.env['galaxy.external.api.action'].create(pre_action)
                    pre_action_ids.append(pre_action_id.id)
                api_id.write({
                    'pre_action_ids':[fields.Command.set(pre_action_ids)]
                })
            if api['post_action_ids']:
                post_action_ids=[]
                for id in api['post_action_ids']:
                    post_action = self.do_rpc(comm_var, "galaxy.external.api.action",[("id","=",id)]).get("records")
                    if len(post_action)==0:
                        continue
                    else:
                        post_action=post_action[0]
                    post_action['api_id']=api_id.id
                    ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",post_action['ir_actions_server_id'][0])]).get("records")[0]
                    ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                    ir_actions_server_id = self.env['ir.actions.server'].sudo().search([('name','=',ir_actions_server['name'])])
                    if not ir_actions_server_id.exists():
                        ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                    else:
                        ir_actions_server.pop('id')
                        ir_actions_server_id.write(ir_actions_server)
                    post_action['ir_actions_server_id']=ir_actions_server_id.id
                    post_action_id = self.env['galaxy.external.api.action'].create(post_action)
                    post_action_ids.append(post_action_id.id)
                
                api_id.write({
                    'post_action_ids':[fields.Command.set(post_action_ids)]
                })
            if api['response_parser_ids']:
            
                for id in api['response_parser_ids']:
                    response_parser = self.do_rpc(comm_var, "galaxy.external.api.resp.parser",[("id","=",id)]).get("records")[0]
                    response_parser['api_id']=api_id.id
                    response_parser_id = self.env['galaxy.external.api.resp.parser'].search([('code','=',response_parser['code'])])
                    if not response_parser_id.exists():
                        response_parser_id = self.env['galaxy.external.api.resp.parser'].create({
                            'api_id':api_id.id,
                            'code':response_parser['code'],
                            'name':response_parser['name'],
                            'remark':response_parser['remark'],
                            'is_default':response_parser['is_default'],
                            'response_codes':response_parser['response_codes']
                        })
                    else:
                        response_parser_id.write({
                            'name':response_parser['name'],
                            'remark':response_parser['remark'],
                            'is_default':response_parser['is_default'],
                            'response_codes':response_parser['response_codes']
                        })
                    action_ids=[]
                    for parser_action_id in response_parser['action_ids']:
                        result_action_list = self.do_rpc(comm_var,'galaxy.external.api.action.parser',[('id','=',parser_action_id)]).get("records")
                        for result_action in result_action_list:
                            action = self.do_rpc(comm_var,'galaxy.external.api.action',[('id','=',result_action['action_id'][0])]).get("records")[0]
                            action['api_id']=api_id.id
                                
                            ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",action['ir_actions_server_id'][0])]).get("records")[0]
                            ir_actions_server_id = self.env['ir.actions.server'].sudo().search([('name','=',ir_actions_server['name'])])
                            ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                            if not ir_actions_server_id.exists():
                                ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                            else:
                                ir_actions_server_id.write(ir_actions_server)
                            action['ir_actions_server_id']=ir_actions_server_id.id
                            
                            result_action_id = self.env['galaxy.external.api.action.parser'].search([('parser_id','=',response_parser_id.id),('action_name','=',action['action_name'])])
                            
                            action_id = self.env['galaxy.external.api.action'].search([('name','=',action['action_name'])])
                            if action_id.exists():
                                action_id.write(action)
                            else:
                                action_id=self.env['galaxy.external.api.action'].create(action)
                            
                            if result_action_id.exists():
                                result_action_id.write({
                                    'rollback':result_action['rollback'],
                                    'sample_data':result_action['sample_data'],
                                })
                            else:
                                result_action_id=self.env['galaxy.external.api.action.parser'].create({
                                    'parser_id':response_parser_id.id,
                                    'rollback':result_action['rollback'],
                                    'sample_data':result_action['sample_data'],
                                    'action_id':action_id.id
                                })
                            action_ids.append(result_action_id.id)
                            if result_action['response_definition_id']:
                                response_definition=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",result_action['response_definition_id'][0])]).get("records")[0]
                                response_definition_id=self.env['galaxy.external.api.definition'].search([('name','=',response_definition['name'])])
                                if not response_definition_id.exists():
                                    response_definition_id=self.env['galaxy.external.api.definition'].create(response_definition)
                                else:
                                    response_definition_id.write({
                                        'name':response_definition['name'],
                                        'params_definition':response_definition['params_definition'],
                                    })
                                result_action_id.write({
                                    'response_definition_id':response_definition_id.id
                                })
                    response_parser_id.write({
                        'action_ids':[fields.Command.set(action_ids)]
                    })        

        self.embed_bind(domain)
    
    def api_update(self, api_id, api, comm_var):
        print('API update：'+api['name'])
        api_dummy=self.env['ir.model'].search([('model','=','galaxy.external.api.dummy')])
        api_id.write({
            'category_id': api['category_id'][0],
            'code': api['code'],
            'name': api['name'],
            'state': api['state'],
            'base_uri': api['base_uri'],
            'base_test_uri': api['base_test_uri'],
            'request_method': api['request_method'],
            'request_body_format': api['request_body_format'],
            'request_header_sample': api['request_header_sample'],
            'request_query_sample': api['request_query_sample'],
            'request_body_sample': api['request_body_sample'],
            'request_files_sample': api['request_files_sample'],
            'request_rargs_sample': api['request_rargs_sample'],
            'description': api['description'],
            'response_raw': api['response_raw'],
            'active': api['active']
        })
        request_header_id=False
        request_query_id=False
        request_body_id=False
        request_files_id=False
        request_rargs_id=False
        auth_id=False
        attachment_ids=[]
        pre_action_ids=[]
        post_action_ids=[]
        response_parser_ids=[]
        request_body_embed_ids=[]
        if api['request_auth']:
            request_auth = self.do_rpc(comm_var,api['request_auth'].split(',')[0],[('id','=',api['request_auth'].split(',')[1])]).get('records')[0]
            request_auth_id = self.env[api['request_auth'].split(',')[0]].search([('name','=',request_auth['name'])])
            if not request_auth_id.exists():
                request_auth_id=self.env[api['request_auth'].split(',')[0]].create({
                    'name':request_auth['name']
                })
            if api['request_auth'].split(',')[0] == "galaxy.external.api.auth.kv":
                kv_definition=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",request_auth['kv_definition_id'][0])]).get("records")[0]
                kv_definition_id = self.env['galaxy.external.api.definition'].search([('name','=',kv_definition['name'])])
                if kv_definition_id.exists():
                    kv_definition_id.write({
                        'type':kv_definition['type'],
                        'params_definition':kv_definition['params_definition']
                    })
                else:
                    kv_definition_id=self.env['galaxy.external.api.definition'].create(kv_definition)
                
                request_auth_id.write({
                    'kv_default_values':request_auth['kv_default_values'],
                    'kv_definition_id':kv_definition_id.id
                })
            auth_id="{},{}".format(api['request_auth'].split(',')[0],request_auth_id.id)
        
        if api['request_header_id']:
            request_header=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_header_id'][0])]).get("records")[0]
            request_header_id = self.env['galaxy.external.api.definition'].search([('name','=',request_header['name'])])
            if not request_header_id.exists():
                request_header_id=self.env['galaxy.external.api.definition'].sudo().create(request_header).id
            else:
                request_header_id.write({
                    'type':request_header['type'],
                    'params_definition':request_header['params_definition']
                })
        if api['request_query_id']:
            request_query=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_query_id'][0])]).get("records")[0]
            request_query_id = self.env['galaxy.external.api.definition'].search([('name','=',request_query['name'])])
            if not request_query_id.exists():
                request_query_id=self.env['galaxy.external.api.definition'].sudo().create(request_query).id
            else:
                request_query_id.write({
                    'type':request_query['type'],
                    'params_definition':request_query['params_definition']
                })
        if api['request_body_id']:
            request_body=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_body_id'][0])]).get("records")[0]
            request_body_id = self.env['galaxy.external.api.definition'].search([('name','=',request_body['name'])])
            if not request_body_id.exists():
                request_body_id=self.env['galaxy.external.api.definition'].sudo().create(request_body).id
            else:
                request_body_id.write({
                    'type':request_body['type'],
                    'params_definition':request_body['params_definition']
                })
        if api['request_files_id']:
            request_files=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_files_id'][0])]).get("records")[0]
            request_files_id = self.env['galaxy.external.api.definition'].search([('name','=',request_files['name'])])
            if not request_files_id.exists():
                request_files_id=self.env['galaxy.external.api.definition'].sudo().create(request_files).id
            else:
                request_files_id.write({
                    'type':request_files['type'],
                    'params_definition':request_files['params_definition']
                })
        if api['request_rargs_id']:
            request_rargs=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",api['request_rargs_id'][0])]).get("records")[0]
            request_rargs_id = self.env['galaxy.external.api.definition'].search([('name','=',request_rargs['name'])])
            if not request_rargs_id.exists():
                request_rargs_id=self.env['galaxy.external.api.definition'].sudo().create(request_rargs).id
            else:
                request_rargs_id.write({
                    'type':request_rargs['type'],
                    'params_definition':request_rargs['params_definition']
                })
        
        if api['request_body_embed_ids']:
            for id in api['request_body_embed_ids']:
                embed = self.do_rpc(comm_var, "galaxy.external.api.embed",[("id","=",id)]).get("records")[0]
                embed_request_body=self.do_rpc(comm_var,'galaxy.external.api.definition',[('id','=',embed['request_body_id'][0])]).get("records")[0]
                embed_request_body_id = self.env['galaxy.external.api.definition'].search([('name','=',embed_request_body['name'])])
                if not embed_request_body_id.exists():
                    embed_request_body_id=self.env['galaxy.external.api.definition'].create(embed_request_body)
                else:
                    embed_request_body_id.write({
                        'params_definition':embed_request_body['params_definition'],
                        'type':embed_request_body['type'],
                    })
                embed['request_body_id']=embed_request_body_id.id
                embed['api_id']=api_id.id
                embed_id = self.env['galaxy.external.api.embed'].search([('name','=',embed['name'])])
                if embed_id.exists():
                    embed_id.unlink()
                embed_id=self.env['galaxy.external.api.embed'].create(embed)
                request_body_embed_ids.append(embed_id.id)
        if api['attachment_ids']:
            for id in api['attachment_ids']:
                attachment = self.do_rpc(comm_var, "galaxy.external.api.attachment",[("id","=",id)]).get("records")[0]
                attachment['api_id']=api_id.id
                attachment_id=self.env['galaxy.external.api.attachment'].create(attachment)
                attachment_ids.append(attachment_id.id)
        if api['pre_action_ids']:
            
            for id in api['pre_action_ids']:
                pre_action = self.do_rpc(comm_var, "galaxy.external.api.action",[("id","=",id)]).get("records")
                if len(pre_action)==0:
                    continue
                else:
                    pre_action=pre_action[0]
                pre_action['api_id']=api_id.id
                ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",pre_action['ir_actions_server_id'][0])]).get("records")[0]
                ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                ir_actions_server_id = self.env['ir.actions.server'].search([('name','=',ir_actions_server['name'])])
                pre_action_id = self.env['galaxy.external.api.action'].search([('action_name','=',pre_action['action_name'])])
                if ir_actions_server_id.exists():
                    ir_actions_server_id.write(ir_actions_server)
                else:
                    ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                pre_action['ir_actions_server_id']=ir_actions_server_id.id
                if pre_action_id.exists():
                    pre_action_id.write(pre_action)
                else:
                    pre_action_id = self.env['galaxy.external.api.action'].create(pre_action)
                pre_action['ir_actions_server_id']=ir_actions_server_id.id
                
                
                pre_action_ids.append(pre_action_id.id)

        if api['post_action_ids']:
            
            for id in api['post_action_ids']:
                post_action = self.do_rpc(comm_var, "galaxy.external.api.action",[("id","=",id)]).get("records")
                if len(post_action)==0:
                    continue
                else:
                    post_action=post_action[0]
                post_action['api_id']=api_id.id
                ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",post_action['ir_actions_server_id'][0])]).get("records")[0]
                ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                ir_actions_server_id = self.env['ir.actions.server'].search([('name','=',ir_actions_server['name'])])
                post_action_id = self.env['galaxy.external.api.action'].search([('action_name','=',post_action['action_name'])])
                
                if ir_actions_server_id.exists():
                    ir_actions_server_id.write(ir_actions_server)
                else:
                    ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                post_action['ir_actions_server_id']=ir_actions_server_id.id
                if post_action_id.exists():
                    post_action_id.write(post_action)
                else:
                    
                    post_action_id = self.env['galaxy.external.api.action'].create(post_action)
                post_action_ids.append(post_action_id.id)
            
        if api['response_parser_ids']:
            
            for id in api['response_parser_ids']:
                response_parser = self.do_rpc(comm_var, "galaxy.external.api.resp.parser",[("id","=",id)]).get("records")[0]
                response_parser['api_id']=api_id.id
                response_parser_id = self.env['galaxy.external.api.resp.parser'].search([('code','=',response_parser['code'])])
                if not response_parser_id.exists():
                    response_parser_id = self.env['galaxy.external.api.resp.parser'].create({
                        'api_id':api_id.id,
                        'code':response_parser['code'],
                        'name':response_parser['name'],
                        'remark':response_parser['remark'],
                        'is_default':response_parser['is_default'],
                        'response_codes':response_parser['response_codes']
                    })
                else:
                    response_parser_id.write({
                        'name':response_parser['name'],
                        'remark':response_parser['remark'],
                        'is_default':response_parser['is_default'],
                        'response_codes':response_parser['response_codes']
                    })
                action_ids=[]
                for parser_action_id in response_parser['action_ids']:
                    result_action_list = self.do_rpc(comm_var,'galaxy.external.api.action.parser',[('id','=',parser_action_id)]).get("records")
                    for result_action in result_action_list:
                        action = self.do_rpc(comm_var,'galaxy.external.api.action',[('id','=',result_action['action_id'][0])]).get("records")[0]
                        action['api_id']=api_id.id
                            
                        ir_actions_server = self.do_rpc(comm_var, "ir.actions.server",[("id","=",action['ir_actions_server_id'][0])]).get("records")[0]
                        ir_actions_server_id = self.env['ir.actions.server'].sudo().search([('name','=','ir.actions.server')])
                        ir_actions_server['model_id']=self.env['ir.model'].search([('model','=',ir_actions_server['model_name'])]).id
                        if not ir_actions_server_id.exists():
                            ir_actions_server_id = self.env['ir.actions.server'].sudo().create(ir_actions_server)
                        else:
                            ir_actions_server_id.write(ir_actions_server)
                        action['ir_actions_server_id']=ir_actions_server_id.id
                        
                        result_action_id = self.env['galaxy.external.api.action.parser'].search([('parser_id','=',response_parser_id.id),('action_name','=',action['action_name'])])
                        
                        action_id = self.env['galaxy.external.api.action'].search([('name','=',action['action_name'])])
                        if action_id.exists():
                            action_id.write(action)
                        else:
                            action_id=self.env['galaxy.external.api.action'].create(action)
                        
                        if result_action_id.exists():
                            result_action_id.write({
                                'rollback':result_action['rollback'],
                                'sample_data':result_action['sample_data'],
                            })
                        else:
                            result_action_id=self.env['galaxy.external.api.action.parser'].create({
                                'parser_id':response_parser_id.id,
                                'rollback':result_action['rollback'],
                                'sample_data':result_action['sample_data'],
                                'action_id':action_id.id
                            })
                        action_ids.append(result_action_id.id)
                        if result_action['response_definition_id']:
                            response_definition=self.do_rpc(comm_var, "galaxy.external.api.definition",[("id","=",result_action['response_definition_id'][0])]).get("records")[0]
                            response_definition_id=self.env['galaxy.external.api.definition'].search([('name','=',response_definition['name'])])
                            if not response_definition_id.exists():
                                response_definition_id=self.env['galaxy.external.api.definition'].create(response_definition)
                            else:
                                response_definition_id.write({
                                    'name':response_definition['name'],
                                    'params_definition':response_definition['params_definition'],
                                })
                            result_action_id.write({
                                'response_definition_id':response_definition_id.id
                            })
                response_parser_id.write({
                    'action_ids':[fields.Command.set(action_ids)]
                })        
                response_parser_ids.append(response_parser_id.id)
        api_id.write({
                'request_header_id':request_header_id,
                'request_query_id':request_query_id,
                'request_body_id':request_body_id,
                'request_files_id':request_files_id,
                'request_rargs_id':request_rargs_id,
                'request_auth':auth_id,
                'request_body_embed_ids':[fields.Command.set(request_body_embed_ids)],
                'attachment_ids':[fields.Command.set(attachment_ids)],
                'pre_action_ids':[fields.Command.set(pre_action_ids)],
                'post_action_ids':[fields.Command.set(post_action_ids)],
                'response_parser_ids':[fields.Command.set(response_parser_ids)]
            })
    
    def embed_bind(self,domain=[]):
        comm_var={'rpc':requests.Session(),'base_url':self.url}
        context = do_rpc_login(comm_var, self.db_name, self.username, self.password)
        comm_var['rpc_context'] = context.get('user_context')
        api_ids = self.env['galaxy.external.api'].search(domain)
        embeds = self.env['galaxy.external.api.embed'].search([('api_id.id','in',api_ids.ids)])
        for embed in embeds:
            raw_embed = self.do_rpc(comm_var,'galaxy.external.api.embed',[('name','=',embed.name)]).get('records')
            if len(raw_embed)==0:
                continue
            raw_embed=raw_embed[0]
            request_body_id = self.env['galaxy.external.api.definition'].search([('name','=',raw_embed['request_body_id'][1])])
            raw_samples = raw_embed['request_body_sample']
            for raw_sample in raw_samples:
                if raw_sample['type']=='many2one' and raw_sample['value']:
                    sample_curr = self.env[raw_sample['comodel']].search([('name','=',raw_sample['value'][1])])
                    raw_sample['value']=[sample_curr.id,sample_curr.name]
                if raw_sample['type']=='many2many' and raw_sample['value']:
                    values=[]
                    for velue_item in raw_sample['value']:
                        value_id = self.env[raw_sample['comodel']].search([('name','=',velue_item[1])])
                        values.append([value_id.id,value_id.name])
                    raw_sample['value']=values
            embed.write({
                'request_body_id':request_body_id.id,
                'request_body_sample':raw_samples
            })
        # apis = self.env['galaxy.external.api'].search([])
        for api in api_ids:
            raw_api = self.do_rpc(comm_var,'galaxy.external.api',[('code','=',api.code)]).get('records')
            if len(raw_api)==0:
                continue
            raw_api=raw_api[0]
            request_body_sample=raw_api['request_body_sample']
            request_header_sample=raw_api['request_header_sample']
            request_query_sample=raw_api['request_query_sample']
            request_files_sample=raw_api['request_files_sample']
            request_rargs_sample=raw_api['request_rargs_sample']
            for curr in request_body_sample:
                if curr.get('type') == 'many2one':
                    raw_curr = list(filter(lambda x: x.get('name') == curr.get('name'), raw_api['request_body_sample']))[0]
                    if raw_curr['value']:
                        embed = self.env[raw_curr['comodel']].search([('name','=',raw_curr['value'][1])])
                        curr['value']=[embed.id,embed.name]
                if curr.get('type')=='many2many' and raw_sample['value'] and curr.get('value'):
                    values=[]
                    for velue_item in curr.get('value'):
                        value_id = self.env[raw_sample['comodel']].search([('name','=',velue_item[1])])
                        values.append([value_id.id,value_id.name])
                    curr['value']=values
            for curr in request_header_sample:
                if curr.get('type') == 'many2one':
                    raw_curr = list(filter(lambda x: x.get('name') == curr.get('name'), raw_api['request_header_sample']))[0]
                    if raw_curr['value']:
                        embed = self.env[raw_curr['comodel']].search([('name','=',raw_curr['value'][1])])
                        curr['value']=[embed.id,embed.name]
            for curr in request_query_sample:
                if curr.get('type') == 'many2one':
                    raw_curr = list(filter(lambda x: x.get('name') == curr.get('name'), raw_api['request_query_sample']))[0]
                    if raw_curr['value']:
                        embed = self.env[raw_curr['comodel']].search([('name','=',raw_curr['value'][1])])
                        curr['value']=[embed.id,embed.name]
            for curr in request_files_sample:
                if curr.get('type') == 'many2one':
                    raw_curr = list(filter(lambda x: x.get('name') == curr.get('name'), raw_api['request_files_sample']))[0]
                    if raw_curr['value']:
                        embed = self.env[raw_curr['comodel']].search([('name','=',raw_curr['value'][1])])
                        curr['value']=[embed.id,embed.name]
            for curr in request_rargs_sample:
                if curr.get('type') == 'many2one':
                    raw_curr = list(filter(lambda x: x.get('name') == curr.get('name'), raw_api['request_rargs_sample']))[0]
                    if raw_curr['value']:
                        embed = self.env[raw_curr['comodel']].search([('name','=',raw_curr['value'][1])])
                        curr['value']=[embed.id,embed.name]
            api.write({
                'request_body_sample':request_body_sample,
                'request_header_sample':request_header_sample,
                'request_query_sample':request_query_sample,
                'request_files_sample':request_files_sample,
                'request_rargs_sample':request_rargs_sample,
            })