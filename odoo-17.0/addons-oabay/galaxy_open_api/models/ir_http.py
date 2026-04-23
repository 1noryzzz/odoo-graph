# -*- coding: utf-8 -*-

import odoo
import logging
import time
import json

from odoo import models,api
from odoo.http import request, SessionExpiredException
from odoo.exceptions import AccessDenied, UserError, ValidationError, AccessError
from werkzeug.exceptions import BadRequest

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    # @classmethod
    # def _is_allowed_cookie(cls, cookie_type):
    #     if request.httprequest.path.startswith('/openapi'):
    #         return False
    #     else:
    #         return super()._is_allowed_cookie(cookie_type)

    @classmethod
    def _auth_method_openapi(cls):
        galaxy_token = request.httprequest.headers.get("X-GALAXY-ACCESS-TOKEN")
        api_key = request.httprequest.headers.get('X-GALAXY-API-KEY')
        if not galaxy_token or not api_key:
            raise BadRequest('Access token missing')

        if galaxy_token.startswith('Bearer '):
            galaxy_token = galaxy_token[7:]
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]

        # if not request.session.is_explicit:
        #     raise SessionExpiredException()

        # 如果galaxy_token已过期，则在http.py 中，它获到不到原来的session_id，于是会新建一个session_id
        # 下面这个查询就会查不到api_app，所以这里不需要再对过期的galaxy_token做任何额外的处理
        api_app = request.env['galaxy.open.api.app'].sudo().search([
            ('key_ids.access_token', '=', galaxy_token),
            ('key_ids.session_id', '=', request.session.sid),
        ], limit=1)
        _logger.info(
            f'第三方应用: {api_app.name}； 接口: {request.httprequest.path}')

        # IP 名单验证
        if api_app.enable_allow_list and api_app.allow_list:
            if request.httprequest.remote_addr not in api_app.allow_list.split('\n'):
                raise AccessDenied('Access Denied')
        if api_app.enable_deny_list and api_app.deny_list:
            if request.httprequest.remote_addr in api_app.deny_list.split('\n'):
                raise AccessDenied('Access Denied')

        # TODO: 验证当前api_app是否有权限访问当前接口

        # 在 galaxy_open_api_log 里留下记录，存下请求信息
        jsonrequest = request.get_json_data()
        openapi_log = request.env['galaxy.open.api.log'].sudo().create({
            'api_app_id':api_app.id,
            'ip':request.httprequest.remote_addr,
            'uri':request.httprequest.path,
            'request_data': jsonrequest
        })

        jsonrequest['openapi_log_id'] = openapi_log.id
        request.httprequest.data = (json.dumps(jsonrequest)).encode('utf-8')
        # redis_dbsource = request.env['base.external.dbsource'].search(
        #     [('name', '=', 'open_api_cache')])
        # if redis_dbsource.exists():
        #     with redis_dbsource.connection_open() as db:
        #         request_id = jsonrequest.get('id')
        #         db.setex(name=f'OPENAPI_RPC_{request_id}', value=openapi_log.id, time=15)

        user_id = request.env["res.users.apikeys"].sudo()._check_credentials(
            'galaxy_token', galaxy_token, scope='galaxy.open.api', key=api_key)
        if not api_app or not user_id:
            raise BadRequest('Access token invalid')

        # take the identity of the API key user
        request.update_env(user=user_id)

    # @classmethod
    # def _auth_method_token(cls):
    #     access_token = request.httprequest.headers.get('Authorization')
    #     if not access_token:
    #         raise BadRequest('Access token missing')

    #     if access_token.startswith('Bearer '):
    #         access_token = access_token[7:]

    #     user_id = request.env["res.users.apikeys"]._check_credentials(
    #         scope='galaxy.open.api', key=access_token)
    #     if not user_id:
    #         raise BadRequest('Access token invalid')

    #     # take the identity of the API key user
    #     request.update_env(user=user_id)

    @classmethod
    def _handle_error(cls, exception):
        if request.httprequest.path.startswith('/openapi'):
            response = {
                'jsonrpc': '2.0',
                'id': request.get_json_data().get('id') if isinstance(request.dispatcher, odoo.http.JsonRPCDispatcher) else int(time.time()),
            }

            error = None
            if isinstance(exception, BadRequest):
                error = {
                    'code': 40001,
                    'message': exception.description,
                }
            elif isinstance(exception, AccessDenied):
                error = {
                    'code': 40002,
                    'message': 'Access Denied',
                }
            elif isinstance(exception, AccessError):
                error = {
                    'code': 40003,
                    'message': exception.args[0],
                }
            elif isinstance(exception, UserError):
                error = {
                    'code': 40008,
                    'message': exception.args[0],
                }
            elif isinstance(exception, ValidationError):
                error = {
                    'code': 40009,
                    'message': exception.args[0],
                }
            elif isinstance(exception, SessionExpiredException):
                error = {
                    'code': 100,
                    'message': 'Token已过期，请刷新！',
                }

            if error is not None:
                response['error'] = error

            return request.make_json_response(response)

        return super()._handle_error(exception)

    @classmethod
    def _post_dispatch(cls, response):
        # 把响应记录到前面的请求日志中去
        if request.httprequest.path.startswith('/openapi'):
            try:
                jsonrequest = json.loads(request.httprequest.data.decode('utf-8'))
                openapi_log_id = jsonrequest.get('openapi_log_id')
                if openapi_log_id and isinstance(openapi_log_id,int):
                    openapi_log = request.env['galaxy.open.api.log'].sudo().browse(openapi_log_id)
                    openapi_log.sudo().write({
                        'response_data':json.loads(response.data.decode('utf-8'))
                    })
            except Exception:
                pass
        # redis_dbsource = request.env['base.external.dbsource'].search(
        #     [('name', '=', 'open_api_cache')])
        # if redis_dbsource.exists():
        #     with redis_dbsource.connection_open() as db:
        #         openapi_log_id = db.get(name=f'OPENAPI_RPC_{response.get('id')}')
        #         if openapi_log_id:
        #             openapi_log = request.env['galaxy.open.api.log'].browse(int(openapi_log_id.decode('utf-8')))
        #             # openapi_log.write({
        #             #     ''
        #             # })
        super()._post_dispatch(response)
