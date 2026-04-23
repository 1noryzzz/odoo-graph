# -*- coding: utf-8 -*-

import json
import time
import base64
import requests

BASE_URL = 'https://demo.ysb.yzbfp.com'
DB_NAME = 'ysb_2'
LOGIN = 'ferrenliu@163.com'
PASSWORD = '123456'

def _do_rpc_login(comm_var, db, login, password):
    # allowed_company_ids
    result = comm_var.get('rpc').post(''.join([
        comm_var.get('base_url'), 'web/session/authenticate']), json={
            'id': int(time.time()),
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'db': db,
                'login': login,
                'password': password,
            }
    })
    # print(result.text)
    return json.loads(result.text).get('result')

def do_rpc_login(comm_var,db, login, password):
    result = requests.post(''.join([
        BASE_URL, '/web/session/authenticate']), json={
            'db': db,
                'login': login,
                'password': password,
            'params': {
                'db': db,
                'login': login,
                'password': password,
            }
    })
    for cookie in result.cookies:
        if cookie.name == 'session_id':
            comm_var['session_id'] = cookie.value
    return json.loads(result.text).get('result')

def do_rpc(comm_var, call_kw, params):
    model = params.get('model')
    if not comm_var.get('session_id'):
        do_rpc_login(comm_var, DB_NAME, LOGIN, PASSWORD)

    result = requests.post(f"{BASE_URL}/web/dataset/call_kw/{model}/web_search_read",
        headers={"X-Openerp-Session-Id":comm_var.get('session_id')},
        json={
            "id": 19,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": "web_search_read",
                "args": [],
                "kwargs": {
                    "domain": params.get('domain'),
                    "fields": params.get('fields')
                }
            }
        })
    return json.loads(result.text).get('result')


# def do_rpc(comm_var, call_kw, params):
#     # https://sales.yzbfp.com/ sales
#     # https://cloud.oabay.com/ gar
#     comm_var['base_url'] = 'https://cloud.oabay.com/'


#     if comm_var.get('rpc') == None:
#         session = requests.Session()

#         comm_var['rpc'] = session
#         context = _do_rpc_login(
#             comm_var, 'gar', 'migrate@163.com', 'abcd1234')
#         comm_var['rpc_context'] = context.get('user_context')
#     result = comm_var.get('rpc').post(
#         ''.join([comm_var.get('base_url'), 'web/dataset/', call_kw]),
#         json={
#             'id': int(time.time()),
#             'jsonrpc': '2.0',
#             'method': 'call',
#             'params': params,
#         })
#     return json.loads(result.text).get('result')
