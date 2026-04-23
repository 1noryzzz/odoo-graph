# -*- coding: utf-8 -*-

import logging
import json

import odoo
import odoo.modules.registry

from werkzeug.exceptions import ServiceUnavailable
from datetime import timedelta
from odoo import fields, http
from odoo.http import dispatch_rpc, db_filter, Controller, request, route, SessionExpiredException
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url
from odoo.exceptions import AccessError, UserError, AccessDenied

_logger = logging.getLogger(__name__)


class OpenApiController(Controller):
    def _refresh_session(self, db, pre_uid):
        registry = odoo.modules.registry.Registry(db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, pre_uid, {})

            user = env['res.users'].browse(pre_uid)
            user_context = dict(env['res.users'].context_get())
            request.session.update({
                'login': user.login,
                'uid': user.id,
                'context': user_context,
                'session_token': env.user._compute_session_token(request.session.sid),
            })

    def _openapi(self, service):
        """Common method to handle an XML-RPC request."""
        data = request.httprequest.get_data()
        params, method = json.loads(data)
        result = dispatch_rpc(service, method, params)
        return json.dumps((result,), methodresponse=1, allow_none=False)

    # @route('/openapi', type="http", auth="public", cors='*', websocket=True)
    # def openapi(self):
    #     """
    #     Handle the websocket handshake, upgrade the connection if
    #     successfull.
    #     """
    #     is_headful_browser = request.httprequest.user_agent and 'Headless' not in request.httprequest.user_agent.string
    #     if request.registry.in_test_mode() and is_headful_browser:
    #         # Prevent browsers from interfering with the unittests
    #         raise ServiceUnavailable()
    #     return WebsocketConnectionHandler.open_connection(request)

    @route(['/openapi/dummy'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def dummy(self, db):
        return {
            'code': 200,
            'message': 'OK',
            'db': db,
            'uid': request.uid,
            'company_id': request.env.company.id,
        }

    @route('/openapi/token', type='http', auth='none')
    def token(self, **kwargs):
        ensure_db()

        # HTTP_X_FORWARDED_FOR
        # headers = request.httprequest.headers
        # remote_ip = request.httprequest.remote_addr
        headers = [
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'no-store')]
        if kwargs.get('grant_type') != 'client_credential':
            data = json.dumps({
                'code': 40002,
                'message': 'invalid grant_type'
            })
        else:
            remote_ip = request.httprequest.remote_addr
            api_app = request.env['galaxy.open.api.app'].sudo().search([
                '&',
                ('app_id', '=', kwargs.get('appid')),
                ('app_secret', '=', kwargs.get('secret')),
                '&',
                '|',
                ('enable_allow_list', '=', False),
                ('allow_list', 'ilike', remote_ip),
                '|',
                ('enable_deny_list', '=', False),
                ('deny_list', 'not ilike', remote_ip),
            ], limit=1)

            if api_app.id:
                request.update_env(user=api_app.user_id.id, context={
                    **request.env.context,
                    'allowed_company_ids': api_app.company_id.ids,
                })
                api_app = request.env['galaxy.open.api.app'].browse(api_app.id)
                current_time = fields.Datetime.now()
                (is_new, access_key) = api_app.get_access_key(request.session.sid)

                result = {
                    'access_token': access_key.access_token,
                    'expires_in': int((access_key.create_date + timedelta(seconds=access_key.expires_in) - current_time).total_seconds()),
                }
                if is_new:
                    result.update({
                        'api_key': request.env['res.users.apikeys']._generate(
                            'galaxy.open.api', access_key.access_token),
                    })
                data = json.dumps(result)
            else:
                data = json.dumps({
                    'code': 40001,
                    'message': 'invalid credential access_token isinvalid or not latest'
                })

        return request.make_response(data, headers)

    # @route(['/openapi/auth/access_token'], type='json', auth="none", cors="*", methods=['POST', 'OPTIONS'])
    # def auth_access_token(self, db, login, password, base_location=None):
    #     if not db_filter([db]):
    #         raise AccessError("Database not found.")
    #     pre_uid = request.session.authenticate(db, login, password)
    #     if pre_uid != request.session.uid:
    #         # Crapy workaround for unupdatable Odoo Mobile App iOS (Thanks Apple :@) and Android
    #         # Correct behavior should be to raise AccessError("Renewing an expired session for user that has multi-factor-authentication is not supported. Please use /web/login instead.")
    #         return {'uid': None}

    #     request.session.db = db
    #     registry = odoo.modules.registry.Registry(db)
    #     with registry.cursor() as cr:
    #         env = odoo.api.Environment(cr, request.session.uid, request.session.context)
    #         if not request.db and not request.session.is_explicit:
    #             # request._save_session would not update the session_token
    #             # as it lacks an environment, rotating the session myself
    #             http.root.session_store.rotate(request.session, env)
    #             request.future_response.set_cookie(
    #                 'session_id', request.session.sid,
    #                 max_age=http.session_lifetime(), httponly=True
    #             )

    #         scope = 'galaxy.openapi.user'
    #         api_key = request.env['res.users.apikeys']._generate(scope, auth_message['name'])
    #         return env['ir.http'].session_info()

    #     return {'access_token': api_key}
