# -*- coding: utf-8 -*-

import odoo
import logging
import time

from odoo import models
from odoo.http import request, SessionExpiredException
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from functools import reduce
from werkzeug.exceptions import BadRequest
from psycopg2.errors import DataError

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _is_allowed_cookie(cls, cookie_type):
        if request.httprequest.path.startswith("/qqapi"):
            return False
        else:
            return super()._is_allowed_cookie(cookie_type)

    @classmethod
    def _authenticate(cls, endpoint):
        super()._authenticate(endpoint)

        access_key = request.env.context.get("galaxy_qq_app")
        if access_key:
            validate_appcode = endpoint.routing.get("appcode")
            allow_versions = endpoint.routing.get("allow_vers")

            if (validate_appcode and validate_appcode != access_key.app_code) or (
                allow_versions
                and request.session.qq_api_version
                and not reduce(
                    lambda prev, curr: (
                        prev
                        if prev
                        else request.session.qq_api_version.startswith(curr)
                    ),
                    allow_versions,
                    False,
                )
            ):
                raise BadRequest("AppCode or Version not allowed!")

    @classmethod
    def _auth_method_qq_token(cls):
        galaxy_token = request.httprequest.headers.get("X-GALAXY-ACCESS-TOKEN")
        if not galaxy_token:
            raise BadRequest("Access token missing")

        if galaxy_token.startswith("Bearer "):
            galaxy_token = galaxy_token[7:]

        # if not request.session.is_explicit:
        #     raise SessionExpiredException()

        # 如果galaxy_token已过期，则在http.py 中，它获到不到原来的session_id，于是会新建一个session_id
        # 下面这个查询就会查不到qq_app，所以这里不需要再对过期的galaxy_token做任何额外的处理
        access_key = (
            request.env["galaxy.qq.app"]
            .sudo()
            .search(
                [
                    (
                        ("qq_user_ids.email", "=", request.session.email)
                        if request.session.login_type == "email"
                        else ("qq_user_ids.mobile", "=", request.session.mobile)
                    ),
                    ("qq_user_ids.key_ids.access_token", "=", galaxy_token),
                    ("qq_user_ids.key_ids.session_id", "=", request.session.sid),
                ],
                limit=1,
            )
        )
        request.update_env(
            context={
                **request.env.context,
                "galaxy_qq_app": access_key,
                "access_token": galaxy_token,
            }
        )

        if request.env.uid is None:
            request.update_env(user=access_key.user_id.id)

        if not access_key:
            raise SessionExpiredException()

    @classmethod
    def _auth_method_qq_apikey(cls):
        api_key = request.httprequest.headers.get("X-GALAXY-API-KEY")
        if not api_key:
            raise BadRequest("Access token missing")
        cls._auth_method_qq_token()

        if api_key.startswith("Bearer "):
            api_key = api_key[7:]

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token",
                (
                    request.session.email
                    if request.session.login_type == "email"
                    else request.session.mobile
                ),
                scope="galaxy.qq.api",
                key=api_key,
            )
        )
        if not pre_uid or pre_uid != request.session.uid:
            raise AccessDenied("用户已在其他设备登录，请重新登录！")

    @classmethod
    def _handle_error(cls, exception):
        if request.httprequest.path.startswith("/qqapi"):
            response = {
                "jsonrpc": "2.0",
                "id": (
                    request.dispatcher.request_id
                    if isinstance(request.dispatcher, odoo.http.JsonRPCDispatcher)
                    else int(time.time())
                ),
            }

            error = None
            if isinstance(exception, BadRequest):
                error = {
                    "code": 40001,
                    "message": exception.description,
                }
            elif isinstance(exception, AccessDenied):
                error = {
                    "code": 40002,
                    "message": exception.args[0],
                }
            elif isinstance(exception, UserError):
                error = {
                    "code": 40008,
                    "message": exception.args[0],
                }
            elif isinstance(exception, ValidationError):
                error = {
                    "code": 40009,
                    "message": exception.args[0],
                }
            elif isinstance(exception, DataError):
                error = {
                    "code": 40080,
                    "message": "Data Error",
                }
            elif isinstance(exception, AccessError):
                error = {
                    "code": 10010,
                    "message": exception.args[0],
                }
            elif isinstance(exception, SessionExpiredException):
                error = {
                    "code": 100,
                    "message": "Token已过期，请刷新！",
                }

            if error is not None:
                response["error"] = error

            return request.make_json_response(response)

        return super()._handle_error(exception)
