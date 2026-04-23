# -*- coding: utf-8 -*-

import logging
import random

from . import galaxy_qq_app
from cache_base import retrieve_cache_base
from datetime import timedelta
from odoo import _, api, models, fields, http
from odoo.exceptions import ValidationError
from odoo.http import request
from functools import reduce

_logger = logging.getLogger(__name__)

VERIFICATION_CODE_PREFIX = "galaxy_qq_api_verification_code"
VERIFICATION_CODE_EXPIRES_IN = 3 * 60


class GalaxyQqUsers(models.Model):
    _name = "galaxy.qq.users"
    _inherit = ["uuid.short.mixin"]
    _description = "APP前端用户"
    _order = "create_date desc"
    _rec_name = "user_name"

    user_id = fields.Many2one(
        "res.users", string="系统用户", ondelete="restrict", required=True
    )
    user_name = fields.Char(string="名称", related="user_id.name")
    app_id = fields.Many2one(
        "galaxy.qq.app", string="APP", ondelete="restrict", requried=True, index=True
    )
    mobile = fields.Char(string="手机号", index=True, copy=False)
    email = fields.Char(string="邮箱", index=True, copy=False)
    key_ids = fields.One2many("galaxy.qq.user.keys", "qq_user_id", string="Keys")

    payment_password = fields.Char(string="支付密码", copy=False)
    login_time = fields.Datetime(
        string="最后登录时间", compute="_compute_last_key", store=True
    )
    login_ip = fields.INet(string="最后登录IP", compute="_compute_last_key", store=True)
    login_country = fields.Char(string="国家", compute="_compute_last_key", store=True)
    login_city = fields.Char(string="城市", compute="_compute_last_key", store=True)
    login_phone_model = fields.Char(
        string="手机型号", compute="_compute_last_key", store=True
    )

    _sql_constraints = [
        (
            "app_id_mobile_email_unique",
            "unique(app_id, mobile, email)",
            "手机号或邮箱必须唯一",
        )
    ]

    @api.constrains("app_id", "mobile", "email")
    def _check_user_exists(self):
        result_by_mobile = self._read_group(
            domain=[("mobile", "!=", False)],
            groupby=["app_id", "mobile"],
            aggregates=["id:recordset"],
            having=[("__count", ">", 1)],
        )
        for _app_id, mobile, _qq_users in result_by_mobile:
            raise ValidationError(
                _(
                    '手机号码 "%s" 已经存在',
                    mobile,
                )
            )

        result_by_email = self._read_group(
            domain=[("email", "!=", False)],
            groupby=["app_id", "email"],
            aggregates=["id:recordset"],
            having=[("__count", ">", 1)],
        )
        for _app_id, email, _qq_users in result_by_email:
            raise ValidationError(
                _(
                    '邮箱 "%s" 已经存在',
                    email,
                )
            )

    @api.depends("key_ids", "key_ids.write_date")
    def _compute_last_key(self):
        for record in self:
            last_info = {
                "login_time": False,
                "login_ip": False,
                "login_country": False,
                "login_city": False,
                "login_phone_model": False,
            }
            if record.key_ids:
                last_key_id = record.key_ids[0]
                last_info.update(
                    {
                        "login_time": last_key_id.write_date,
                        "login_ip": last_key_id.ip,
                        "login_country": last_key_id.country_id.name if last_key_id.country_id else '',
                        "login_city": last_key_id.city,
                        "login_phone_model": last_key_id.phone_model,
                    }
                )
                record.update(last_info)

    def generate_verification_code(
        self, login_with, expires_in=VERIFICATION_CODE_EXPIRES_IN
    ):
        chars = "0123456789"
        verification_code = "".join(
            random.SystemRandom().choice(chars) for _ in range(6)
        )
        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            db.setex(
                name=f"{VERIFICATION_CODE_PREFIX}_{self.app_id.app_code}_{login_with}",
                value=verification_code,
                time=expires_in,
            )
        return verification_code

    def check_verification_code(self, verification_code, login_with=None):
        if not login_with:
            login_with = self.mobile
        verify = False
        cache_base = retrieve_cache_base(self.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            vfcode = db.getdel(
                f"{VERIFICATION_CODE_PREFIX}_{self.app_id.app_code}_{login_with}"
            )
            if vfcode and vfcode.decode("utf-8") == verification_code:
                verify = True

        return verify

    def get_access_key(self, sid, login_with, platform_os, phone_model):
        self.ensure_one()

        last_key = reduce(
            lambda x, y: x if x and x.create_date > y.create_date else y,
            self.key_ids.filtered(lambda key: key.session_id == sid),
            None,
        )
        if last_key and last_key.id and not last_key.is_invalid:
            current_time = fields.Datetime.now()
            expires_time = last_key.create_date + timedelta(seconds=last_key.expires_in)
            remaining = (expires_time - current_time).total_seconds()
            if remaining > galaxy_qq_app.SAFE_GAP:
                return (False, last_key)

        # 仅当用户登录时，才会强制失效其它的Token
        # self.key_ids.filtered(
        #     lambda key: not (key.force_invalid or key.is_invalid)).invalid_old_keys()
        access_key = (
            self.env["galaxy.qq.user.keys"]
            .sudo()
            .create(
                {
                    "qq_user_id": self.id,
                    "access_token": self.short_uuid4(length=32),
                    "session_id": sid,
                    "expires_in": galaxy_qq_app.EXPIRES_IN,
                    "login_with": login_with,
                    "ip": request.httprequest.remote_addr if request else "n/a",
                    "platform_os": platform_os,
                    "phone_model": phone_model,
                }
            )
        )
        cache_base = retrieve_cache_base(self.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            db.setex(
                name=f"{http.TOKEN_PREFIX}{access_key.access_token}",
                value=sid,
                time=access_key.expires_in,
            )

        return (True, access_key)

    def unlink(self):
        self.ensure_one()

        self.key_ids.sudo().unlink()
        return super().unlink()
