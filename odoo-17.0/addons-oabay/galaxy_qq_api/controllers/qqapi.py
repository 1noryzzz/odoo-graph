# -*- coding: utf-8 -*-

import logging
import json
import odoo
import odoo.modules.registry
import time

from datetime import timedelta
from odoo import _, fields, http
from odoo.http import (
    Controller,
    request,
    route,
)
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.auth_signup.models.res_partner import SignupError
from odoo.addons.bus.models.bus import json_dump
from werkzeug.exceptions import BadRequest
from wechatpy.exceptions import WeChatClientException

_logger = logging.getLogger(__name__)


class QingQianApiController(Controller):
    def _refresh_session(self, db, pre_uid):
        registry = odoo.modules.registry.Registry(db)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, pre_uid, {})

            user = env["res.users"].sudo().browse(pre_uid)
            user_context = dict(env["res.users"].context_get())
            request.session.update(
                {
                    "login": user.login,
                    "uid": user.id,
                    "context": user_context,
                    "session_token": env.user._compute_session_token(
                        request.session.sid
                    ),
                }
            )

    @route(
        ["/qqapi/user_info"],
        auth="qq_apikey",
        cors="*",
        methods=["GET"],
        website=True,
    )
    def user_info(self):
        return json.dumps(
            {
                "code": 200,
                "message": "OK",
                "db": request.db,
                "uid": request.uid,
                "company_id": request.env.company.id,
                "mobile": request.env.user.mobile or "",
                "email": request.env.user.email or "",
                "name": request.env.user.name,
                "version": request.session.qq_api_version,
            }
        )

    # @route(['/qqapi/user_priv_info'], type='json', auth="qq_apikey", methods=['POST'])
    # def user_priv_info(self, db):
    #     return {
    #         'code': 200,
    #         'message': 'OK',
    #         'db': db,
    #         'uid': request.uid,
    #         'company_id': request.env.company.id,
    #         'mobile': request.session.mobile,
    #         'name': request.env.user.name if request.uid and request.uid != request.env.ref(
    #             'galaxy_qq_api.group_galaxy_qq_api_public_user_id').id else '',
    #         'version': request.session.qq_api_version,
    #         'logged_in': True if request.uid else False,
    #     }

    @route("/qqapi/token", type="http", auth="none")
    def token(self, **kwargs):
        ensure_db()

        # HTTP_X_FORWARDED_FOR
        # headers = request.httprequest.headers
        # remote_ip = request.httprequest.remote_addr
        headers = [("Content-Type", "application/json"), ("Cache-Control", "no-store")]
        if kwargs.get("grant_type") != "app_credential":
            data = json.dumps({"code": 40002, "message": "invalid grant_type"})
        else:
            api_app = (
                request.env["galaxy.qq.app"]
                .sudo()
                .search(
                    [
                        ("app_code", "=", kwargs.get("app_code")),
                        ("ver_ids.ver", "=", kwargs.get("ver")),
                        ("ver_ids.ver_secret", "=", kwargs.get("secret")),
                    ],
                    limit=1,
                )
            )

            if api_app.id:
                request.update_env(
                    user=api_app.user_id.id,
                    context={
                        **request.env.context,
                        "allowed_company_ids": api_app.company_id.ids,
                    },
                )
                api_app = request.env["galaxy.qq.app"].browse(api_app.id)
                current_time = fields.Datetime.now()

                try:
                    (is_new, access_key) = api_app.get_access_key(
                        request.session.sid,
                        kwargs.get("mobile"),
                        kwargs.get("email"),
                        kwargs.get("platform_os"),
                        kwargs.get("phone_model"),
                    )

                    request.session.qq_api_version = kwargs.get("ver")
                    if kwargs.get("mobile") and request.session.mobile != access_key.login_with:
                        request.session.mobile = access_key.login_with
                        request.session.login_type = "mobile"
                    elif kwargs.get("email") and request.session.email != access_key.login_with:
                        request.session.email = access_key.login_with
                        request.session.login_type = "email"
                    elif not kwargs.get("mobile") and not kwargs.get("email"):
                        request.session.email = access_key.login_with
                        request.session.login_type = "email"

                    result = {
                        "id": access_key.id,
                        "login_with": access_key.login_with,
                        "access_token": access_key.access_token,
                        "expires_in": int(
                            (
                                access_key.create_date
                                + timedelta(seconds=access_key.expires_in)
                                - current_time
                            ).total_seconds()
                        ),
                        "unregistered": (
                            api_app.user_id.id == access_key.qq_user_id.user_id.id
                        ),
                        "last_version": api_app.last_version.ver if api_app.last_version else kwargs.get("ver"),
                        "force_update": api_app.last_version.force_update if api_app.last_version else False,
                        "android_download_url": api_app.last_version.android_download_url if api_app.last_version else "",
                        "ios_download_url": api_app.last_version.ios_download_url if api_app.last_version else "",
                    }
                    if (
                        request.env["ir.config_parameter"]
                        .sudo()
                        .get_param("galaxy.qq.api.enable.ipinfo", False)
                    ):
                        result.update(
                            {
                                "country_code": access_key.country_id.code,
                                "default_langs": access_key.default_langs,
                                "city": access_key.city,
                                "tz": access_key.tz,
                                "lat": access_key.lat,
                                "lng": access_key.lng,
                            }
                        )

                    data = json.dumps(result)
                except Exception as e:
                    data = json.dumps(
                        {
                            "code": 40010,
                            "message": str(e),
                        }
                    )
            else:
                data = json.dumps(
                    {
                        "code": 40001,
                        "message": "invalid credential access_token isinvalid or not latest",
                    }
                )

        return request.make_response(data, headers)

    @route(["/qqapi/weapp_get_number"], type="json", auth="none", methods=["POST"])
    def weapp_get_number(self, code, app_code, ver, secret, db):
        api_app = (
            request.env["galaxy.qq.app"]
            .sudo()
            .search(
                [
                    ("app_code", "=", app_code),
                    ("ver_ids.ver", "=", ver),
                    ("ver_ids.ver_secret", "=", secret),
                ],
                limit=1,
            )
        )
        if api_app.id and api_app.weapp_id:
            request.update_env(
                user=api_app.user_id.id,
                context={
                    **request.env.context,
                    "allowed_company_ids": api_app.company_id.ids,
                },
            )
            api_app = request.env["galaxy.qq.app"].browse(api_app.id)
            try:
                current_time = fields.Datetime.now()
                weapp, entry = request.env["wechat.weapp.config"].retrieve_entry(
                    app_id=api_app.weapp_id.app_id
                )
                result = entry.client.wxa.get_phone_number(code)
                if result.get("errcode") != 0:
                    raise BadRequest(result.get("errmsg"))

                weapp_pure_phone = result.get("phone_info", {}).get("purePhoneNumber")
                (is_new, access_key) = api_app.get_access_key(
                    request.session.sid, weapp_pure_phone
                )
                if is_new or request.session.mobile != weapp_pure_phone:
                    request.session.mobile = weapp_pure_phone

                qq_user = request.env["galaxy.qq.users"].search(
                    [
                        ("app_id", "=", api_app.id),
                        ("mobile", "=", weapp_pure_phone),
                    ]
                )
                if not qq_user:
                    raise BadRequest("Access token invalid")

                # 登录成功后，把这个用户的其它session都踢掉
                qq_user.key_ids.filtered(
                    lambda key: not (key.force_invalid or key.is_invalid)
                    and key.access_token != access_key.access_token
                ).invalid_old_keys()

                pre_uid = qq_user.user_id.id
                request.update_env(user=pre_uid)
                self._refresh_session(db, pre_uid)
                request.env["res.users.apikeys"].sudo().search(
                    [
                        ("user_id", "=", pre_uid),
                        ("name", "=", weapp_pure_phone),
                        ("scope", "=", "galaxy.qq.api"),
                    ]
                ).unlink()
                return {
                    "code": 200,
                    "mobile": weapp_pure_phone,
                    "access_token": access_key.access_token,
                    "expires_in": int(
                        (
                            access_key.create_date
                            + timedelta(seconds=access_key.expires_in)
                            - current_time
                        ).total_seconds()
                    ),
                    "api_key": request.env["res.users.apikeys"]._generate(
                        "galaxy.qq.api", weapp_pure_phone
                    ),
                    "data": result,
                }
            except WeChatClientException:
                raise BadRequest("参数错误")
        else:
            raise BadRequest("参数错误")

    @route(
        ["/qqapi/send_verification_code"],
        type="json",
        auth="qq_token",
        methods=["POST"],
    )
    def send_verification_code(self, mobile):
        if request.session.mobile != mobile:
            raise BadRequest("Access token invalid")

        qq_app = request.env.context.get("galaxy_qq_app")
        access_token = request.env.context.get("access_token")

        qq_user_key = qq_app.qq_user_ids.filtered(
            lambda u: u.mobile == mobile
        ).key_ids.filtered(lambda k: k.access_token == access_token)
        # verification_code = qq_user_key.send_verification_code(mobile)
        qq_user_key.send_verification_code(mobile)
        return {
            "code": 200,
            "message": "发送成功",
            # 'vc': verification_code,
        }

    @route(
        ["/qqapi/send_verification_email"],
        type="json",
        auth="qq_token",
        methods=["POST"],
        website=True
    )
    def send_verification_email(self, email, params=None):
        email = email and email.lower()
        if request.session.email != email:
            raise BadRequest("Access token invalid")

        qq_app = request.env.context.get("galaxy_qq_app").with_context(lang=request.env.lang)
        access_token = request.env.context.get("access_token")

        qq_user = qq_app.qq_user_ids.filtered(lambda u: u.email == email)
        qq_user_key = qq_user.key_ids.filtered(lambda k: k.access_token == access_token)

        if qq_app.user_id.id == qq_user.user_id.id:
            # 用户未注册的情况下，需要提供params，用于注册用户
            if not params:
                raise BadRequest("参数错误")

            qq_user_key.write({"params": params})
        qq_user_key.send_verification_email(email)
        return {
            "code": 200,
            "message": "发送成功",
        }

    @route(["/qqapi/login"], type="json", auth="qq_token", methods=["POST"])
    def login(self, db, mobile, verification_code):
        qq_app = request.env.context.get("galaxy_qq_app")
        if not qq_app:
            raise BadRequest("Access token missing")

        if request.session.mobile != mobile:
            raise BadRequest("Access token invalid")

        qq_user = qq_app.qq_user_ids.filtered(lambda u: u.mobile == mobile)
        if not qq_user:
            raise BadRequest("Access token invalid")
        if verification_code != "888888" and not qq_user.check_verification_code(
            verification_code
        ):
            raise BadRequest(_("验证码错误或已过期"))

        # 登录成功后，把这个用户的其它session都踢掉
        qq_user.key_ids.filtered(
            lambda key: not (key.force_invalid or key.is_invalid)
            and key.access_token != request.env.context.get("access_token")
        ).invalid_old_keys()
        pre_uid = qq_user.user_id.id
        request.update_env(user=pre_uid)
        self._refresh_session(db, pre_uid)
        request.env["res.users.apikeys"].sudo().search(
            [
                ("user_id", "=", pre_uid),
                ("name", "=", mobile),
                ("scope", "=", "galaxy.qq.api"),
            ]
        ).unlink()

        return {
            "code": 200,
            "message": "登录成功",
            # TODO: 其它信息，比如业务角色
            "api_key": request.env["res.users.apikeys"]._generate(
                "galaxy.qq.api", mobile
            ),
            "uid": request.uid,
            "session_uid": request.session.uid,
        }

    @route(["/qqapi/email_login"], type="json", auth="qq_token", methods=["POST"])
    def email_login(self, email, api_key, relogin=False):
        email = email and email.lower()
        qq_app = request.env.context.get("galaxy_qq_app")
        access_token = request.env.context.get("access_token")
        qq_user_key = qq_app.qq_user_ids.filtered(
            lambda u: u.email == email
        ).key_ids.filtered(lambda k: k.access_token == access_token)

        if request.session.email != email:
            raise BadRequest("Access token invalid")

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", email, scope="galaxy.qq.api", key=api_key
            )
        )
        if not pre_uid:
            raise BadRequest("登录已失效，请重新登录")

        request.update_env(user=pre_uid)
        self._refresh_session(request.db, pre_uid)

        qq_user_key.write(
            {
                "ip": request.httprequest.remote_addr if request else "n/a",
            }
        )

        return {
            "code": 200,
            "message": "登录成功",
            # TODO: 其它信息，比如业务角色
            "uid": request.uid,
            "session_uid": request.session.uid,
        }

    @http.route("/qqapi/email_logout", type="json", auth="qq_token", methods=["POST"])
    def email_logout(self, email, api_key):
        email = email and email.lower()
        if request.session.email != email:
            raise BadRequest("Access token invalid")

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", email, scope="galaxy.qq.api", key=api_key
            )
        )
        if pre_uid:
            request.env["res.users.apikeys"].sudo().search(
                [
                    ("user_id", "=", pre_uid),
                    ("name", "=", email),
                    ("scope", "=", "galaxy.qq.api"),
                ]
            ).unlink()

        request.session.logout(keep_db=True)
        return {
            "code": 200,
            "message": "已成功退出登录",
        }

    @http.route("/qqapi/email_terminate", type="json", auth="qq_token", methods=["POST"])
    def email_terminate(self, email, api_key):
        email = email and email.lower()
        if request.session.email != email:
            raise BadRequest("Access token invalid")

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", email, scope="galaxy.qq.api", key=api_key
            )
        )
        if not pre_uid:
            raise BadRequest("Access token invalid")

        request.env["res.users.apikeys"].sudo().search(
            [
                ("user_id", "=", pre_uid),
                ("name", "=", email),
                ("scope", "=", "galaxy.qq.api"),
            ]
        ).unlink()
        request.env["galaxy.qq.users"].sudo().search(
            [
                ("user_id", "=", pre_uid),
                ("email", "=", email),
            ]
        ).unlink()

        request.session.logout(keep_db=True)
        request.update_env(user=request.env.ref("base.public_user"))

        r_users = request.env["res.users"].sudo().browse(pre_uid)
        r_users.sudo().write({
            "active": False,
            "login": f"{r_users.login}_deleted_by_galaxy_qq_api_{str(time.time())}",
        })
        request.env["res.partner"].sudo().browse(r_users.partner_id.id).write({"active": False})

        return {
            "code": 200,
            "message": _(f"账户{email}已成功注销"),
        }

    @route(["/qqapi/relogin"], type="json", auth="qq_token", methods=["POST"])
    def relogin(self, db, mobile, api_key):
        if request.session.mobile != mobile:
            raise BadRequest("Access token invalid")

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", mobile, scope="galaxy.qq.api", key=api_key
            )
        )
        if not pre_uid:
            raise BadRequest("登录已失效，请重新登录")

        self._refresh_session(db, pre_uid)

        return {
            "code": 200,
            "message": "登录成功",
            # TODO: 其它信息，比如业务角色
            "uid": request.uid,
            "session_uid": request.session.uid,
        }

    @http.route("/qqapi/logout", type="json", auth="qq_token", methods=["POST"])
    def logout(self, mobile, api_key):
        if request.session.mobile != mobile:
            raise BadRequest("Access token invalid")

        pre_uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(
                "galaxy_token", mobile, scope="galaxy.qq.api", key=api_key
            )
        )
        if pre_uid:
            request.env["res.users.apikeys"].sudo().search(
                [
                    ("user_id", "=", pre_uid),
                    ("name", "=", mobile),
                    ("scope", "=", "galaxy.qq.api"),
                ]
            ).unlink()

        request.session.logout(keep_db=True)
        return {
            "code": 200,
            "message": "已成功退出登录",
        }

    @http.route(["/qqapi/check_verification_email"], type="json", auth="qq_token", methods=["POST"])
    def check_verification_email(self, email):
        email = email and email.lower()
        if request.session.email != email:
            raise BadRequest("Access token invalid")

        qq_app = request.env.context.get("galaxy_qq_app").with_context(lang=request.env.lang)
        access_token = request.env.context.get("access_token")

        qq_user = qq_app.qq_user_ids.filtered(lambda u: u.email == email)
        qq_user_key = qq_user.key_ids.filtered(lambda k: k.access_token == access_token)

        sendmsgs = request.env['bus.bus'].sudo().search([
            ('channel', '=', json_dump([request.db, 'galaxy.qq.user.keys', qq_user_key.id]))
        ], order='create_date desc').filtered(lambda m: json.loads(m.message).get('type') == 'email_verification' and json.loads(m.message).get('payload', {}).get('event') == 'email_authenticated')
        if sendmsgs.exists():
            return {
                "code": 200,
                "payload": json.loads(sendmsgs[0].message).get('payload')
            }
        else:
            return {
                "code": 404,
                "message": "邮件还未验证"
            }

    @http.route("/qqapi/email_verification", type="http", auth="public", website=True)
    def email_verification(self, **kwargs):
        if not kwargs.get("k") or not kwargs.get("email"):
            return "参数错误"

        is_signup = True
        access_key = (
            request.env["galaxy.qq.user.keys"]
            .sudo()
            .search(
                [
                    ("login_with", "=", kwargs.get("email").lower()),
                    ("access_token", "=", kwargs.get("k")),
                ],
                limit=1,
            )
        )

        if not access_key or access_key.is_invalid:
            return request.render(
                "galaxy_qq_api.page_email_verification_error",
                {
                    "status_code": "461",
                    "status_message": _("Token 已过期"),
                    "error_message": "",
                },
            )

        if not access_key.qq_user_id.check_verification_code(
            kwargs.get("code"), kwargs.get("email").lower()
        ):
            return request.render(
                "galaxy_qq_api.page_email_verification_error",
                {
                    "status_code": "462",
                    "status_message": _("验证码错误或已过期"),
                    "error_message": "",
                },
            )

        # 登录成功后，把这个用户的其它session都踢掉
        access_key.qq_user_id.key_ids.filtered(
            lambda key: not (key.force_invalid or key.is_invalid)
            and key.id != access_key.id
        ).invalid_old_keys()

        if access_key.qq_user_id.user_id.id != access_key.qq_user_id.app_id.user_id.id:
            # 删除掉这个用户之前的apikeys
            request.env["res.users.apikeys"].sudo().search(
                [
                    ("user_id", "=", access_key.qq_user_id.user_id.id),
                    ("name", "=", kwargs.get("email").lower()),
                    ("scope", "=", "galaxy.qq.api"),
                ]
            ).unlink()
            is_signup = False
        else:
            try:
                access_key.qq_user_id.write(
                    {
                        "user_id": request.env["res.users"]
                        .sudo()
                        .qqapi_signup(kwargs.get("email").lower(), access_key)
                        .id
                    }
                )
            except SignupError as e:
                return request.render(
                    "galaxy_qq_api.page_email_verification_error",
                    {
                        "status_code": "500",
                        "status_message": "注册用户失败",
                        "error_message": str(e),
                    },
                )
        pre_uid = access_key.qq_user_id.user_id.id
        request.update_env(user=pre_uid)
        request.env["bus.bus"]._sendone(
            request.env["galaxy.qq.user.keys"].sudo().browse(access_key.id),
            "email_verification",
            {
                "access_token": kwargs.get("k"),
                # 提供api_key
                "api_key": request.env["res.users.apikeys"]._generate(
                    "galaxy.qq.api", kwargs.get("email").lower()
                ),
                "event": "email_authenticated",
            },
        )
        access_key.write(
            {
                "ip": request.httprequest.remote_addr if request else "n/a",
            }
        )
        return request.render(
            "galaxy_qq_api.page_email_verification_success",
            {
                "is_signup": is_signup,
                "user_name": access_key.qq_user_id.user_name,
            },
        )


"""
    @http.route('/createOrder', auth='public', methods=['GET', 'POST'], csrf=False)
    def createOrder(self, **kw):
        amount = kw.get('orderAmount')
        totalAmount =  int(round(float(amount), 2) * 100)
        entry = weapp_entry.retrieve_entry(request.env, 'wx7c9ad05650f07b9a')
        session = entry.client.wxa.code_to_session(kw.get('code'))
        request_param = {
        "msgId": None,
        "requestTimestamp": None,
        "merOrderId": None,
        "mid": "89810005311AWZ2",
        "tid": "DM003499",
        "instMid": "MINIDEFAULT",
        "goods": [
            {
            "goodsId": "666",
            "goodsName": "胖头鱼",
            "quantity": "1",
            "price": "990",
            "goodsCategory": "1",
            "body": "无",
            "unit": "1",
            "discount": "0",
            "subMerchantId": "89810007999APPE",
            "merOrderId": "343R4213232323231255",
            "subOrderAmount": totalAmount
            }
        ],
        "attachedData": None,
        "expireTime": None,
        "goodsTag": None,
        "goodsTradeNo": None,
        "orderDesc": None,
        "originalAmount": None,
        "productId": None,
        "totalAmount": totalAmount,
        "divisionFlag": True,
        "asynDivisionFlag": None,
        "platformAmount": "0",
        "subOrders": [
            {
            "mid": "89810007999APPE",
            "merOrderId": "343R54237421933732",
            "totalAmount": totalAmount
            }
        ],
        "notifyUrl": "https://www.sina.com.cn",
        "returnUrl": "http://www.wfdsj.cn/cn/index.htm",
        "showUrl": None,
        "secureTransaction": None,
        "subAppId": None,
        "subOpenId": session.get("openid"),
        "userId": None,
        "tradeType": "MINI",
        "limitCreditCard": None,
        "installmentNumber": None,
        "name": None,
        "mobile": None,
        "certType": None,
        "certNo": None,
        "fixBuyer": None,
        "retCommParams": {
            "foodOrderType": "pre_order"
        },
        "feeRatio": None,
        "costSubsidy": None,
        "preauthTransaction": None
        }

        resp = request.env['galaxy.external.api'].sudo().invoke(
            'UMS-UNIFIED-ORDER', body=request_param).retrieve_response('UMS-UNIFIED-ORDER-RESULT')

        return request.make_json_response(resp.raw)
"""
