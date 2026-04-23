# -*- coding: utf-8 -*-

import logging

from . import galaxy_qq_app, galaxy_qq_users
from cache_base import retrieve_cache_base
from datetime import datetime, timedelta, timezone
from odoo import _, api, models, fields, http
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class GalaxyQqUserKeys(models.Model):
    _name = "galaxy.qq.user.keys"
    _inherit = ["galaxy.external.api.response.data.mixin"]
    _description = "前端APP用户的key"
    _order = "create_date desc"

    qq_user_id = fields.Many2one(
        "galaxy.qq.users",
        string="用户",
        index=True,
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    access_token = fields.Char(string="Token", required=True)
    session_id = fields.Char(string="Session ID", required=True)
    expires_in = fields.Integer(string="有效期", required=True)
    expires_date = fields.Datetime(string="过期时间", compute="_compute_expires_date")
    login_with = fields.Char(string="登录方式")
    force_invalid = fields.Boolean(string="强制失效", default=False)
    is_invalid = fields.Boolean(string="已失效", compute="_compute_is_invalid")
    ip = fields.INet(string="IP地址")
    ipinfo_needed = fields.Boolean(string="需要更新IP信息", default=False)
    platform_os = fields.Char(string="操作系统")
    phone_model = fields.Char(string="手机型号")
    country_id = fields.Many2one("res.country", string="国家")
    lat = fields.Float(string="纬度")
    lng = fields.Float(string="经度")
    city = fields.Char(string="城市")
    postal = fields.Char(string="邮编")
    tz = fields.Char(string="时区")
    default_langs = fields.Json(string="可选语言")

    params = fields.Json(
        string="注册参数缓存",
        help="这个字段用于缓存注册时的参数，在注册成功时把这个写入用户表",
    )
    nickname = fields.Char(string="昵称", compute="_compute_user_info")
    lang = fields.Char(string="语言", compute="_compute_user_info")
    verification_code = fields.Char(
        string="验证码", compute="_compute_verification_code"
    )

    @api.autovacuum
    def _gc_invalid_keys(self):
        timeout_ago = datetime.now(timezone.utc) - timedelta(
            seconds=galaxy_qq_app.EXPIRES_IN + galaxy_qq_app.SAFE_GAP
        )
        self.env.cr.execute(
            """
            SELECT id as id
            FROM galaxy_qq_user_keys C
            WHERE NOT EXISTS (
                SELECT 1
                FROM res_users_apikeys M
                WHERE M.name = C.access_token AND m.scope = 'galaxy.qq.api'
            ) AND C.create_date < %s""",
            (timeout_ago.strftime(DEFAULT_SERVER_DATETIME_FORMAT),),
        )
        qq_user_key_ids = [item["id"] for item in self.env.cr.dictfetchall()]
        self.browse(qq_user_key_ids).unlink()

    @api.depends("expires_in")
    def _compute_expires_date(self):
        for record in self:
            record.expires_date = record.create_date + timedelta(
                seconds=record.expires_in
            )

    @api.depends("force_invalid", "expires_in", "create_date")
    def _compute_is_invalid(self):
        current_time = fields.Datetime.now()
        for key in self:
            expires_time = key.create_date + timedelta(seconds=key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining <= 0 or key.force_invalid:
                key.is_invalid = True
            else:
                key.is_invalid = False

    @api.depends("params", "qq_user_id")
    def _compute_user_info(self):
        for key in self:
            if key.qq_user_id.user_id.id != key.qq_user_id.app_id.user_id.id:
                key.nickname = key.qq_user_id.user_name
                key.lang = key.qq_user_id.user_id.lang
            elif key.params:
                key.nickname = key.params.get("nickname", False)
                key.lang = key.params.get("lang", False)
            else:
                key.nickname = ""
                key.lang = ""

    @api.depends("login_with")
    def _compute_verification_code(self):
        for key in self:
            vfcode = ""
            cache_base = retrieve_cache_base(self.env, "TOKEN-CACHE")
            with cache_base.redis_db.connection_open() as db:
                vfcode = db.get(
                    f"{galaxy_qq_users.VERIFICATION_CODE_PREFIX}_{key.qq_user_id.app_id.app_code}_{self.login_with}"
                )
            key.verification_code = vfcode if vfcode else False

    def _get_default_langs(self, country_code):
        return (
            self.env["res.lang"]
            .search([("code", "like", f"_{country_code}")])
            .mapped("code")
        )

    def _get_ipinfo(self, vals=False, user_key=False):
        try:
            req = self.env["galaxy.external.api"].invoke(
                "IPINFO",
                query={
                    "ip": vals.get("ip") if vals else user_key.ip,
                },
            )
            resp_data = req.retrieve_response("IPINFO-RESULT")
            if resp_data:
                result = {
                    "ipinfo_needed": False,
                    "definition_id": resp_data.definition_id.id,
                    "raw": resp_data.raw,
                    "country_id": self.env["res.country"]
                    .search(
                        [("code", "=", resp_data.raw.get("country"))],
                        limit=1,
                    )
                    .id,
                    "lat": resp_data.raw.get("lat"),
                    "lng": resp_data.raw.get("lng"),
                    "city": resp_data.raw.get("city"),
                    "postal": resp_data.raw.get("postal"),
                    "tz": resp_data.raw.get("timezone"),
                    "default_langs": self._get_default_langs(
                        resp_data.raw.get("country")
                    ),
                }

                vals.update(result) if vals else user_key.write(result)
        except Exception as e:
            _logger.warning(f"Failed to get ipinfo: {repr(e)}")

    def retrieve_ipinfo(self):
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("galaxy.qq.api.enable.ipinfo", False)
        ):
            todo_keys = self.search([("ipinfo_needed", "=", True), ("ip", "!=", False)])
            for todo_key in todo_keys:
                self._get_ipinfo(user_key=todo_key)

    def invalid_old_keys(self):
        current_time = fields.Datetime.now()
        cache_base = retrieve_cache_base(self.env, "TOKEN-CACHE")
        for key in self:
            key.force_invalid = True

            expires_time = key.create_date + timedelta(seconds=key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining > galaxy_qq_app.SAFE_GAP:
                # 如果Token的有效时间大于10秒，则改为10秒，即10秒后，此Token失效
                with cache_base.redis_db.connection_open() as db:
                    db.getex(
                        f"{http.TOKEN_PREFIX}{key.access_token}",
                        ex=galaxy_qq_app.SAFE_GAP,
                    )
                    # if session_info:
                    #     db.setex(
                    #         name=f'{http.TOKEN_PREFIX}{key.access_token}', value=session_info, time=galaxy_qq_app.SAFE_GAP)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "ip" in vals and self.env["ir.config_parameter"].sudo().get_param(
                "galaxy.qq.api.enable.ipinfo", False
            ):
                self._get_ipinfo(vals=vals)

        return super().create(vals_list)

    def write(self, vals):
        if "ip" in vals and self.env["ir.config_parameter"].sudo().get_param(
            "galaxy.qq.api.enable.ipinfo", False
        ):
            vals.update({"ipinfo_needed": True})
            self.env["ir.cron.trigger"].sudo().create(
                {
                    "cron_id": self.env.ref("galaxy_qq_api.ir_cron_retrieve_ipinfo").id,
                    "call_at": fields.Datetime.now() + timedelta(seconds=5),
                }
            )

        return super().write(vals)
