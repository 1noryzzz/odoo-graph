# -*- coding: utf-8 -*-

import random
import time

from cache_base import retrieve_cache_base
from odoo import _, api, models, fields
from odoo.exceptions import UserError

DEBOUNCE = 3
EXPIRES_IN = 2 * 60 * 60
SAFE_GAP = 10


class GalaxyQqApp(models.Model):
    """
    TODO: 限制应用的访问权限
    """

    _name = "galaxy.qq.app"
    _inherit = ["image.mixin", "uuid.short.mixin"]
    _description = "青钱闪付APP"

    _sql_constraints = [("app_code_uniq", "unique (app_code)", "APP Code必须唯一！")]

    company_id = fields.Many2one(
        "res.company",
        string="公司",
        required=True,
        default=lambda self: self.env.company,
    )

    name = fields.Char(string="应用名称", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="用户",
        required=True,
        default=lambda self: self.env.ref(
            "galaxy_qq_api.group_galaxy_qq_api_public_user_id"
        ).id,
    )
    app_code = fields.Char(string="应用代码", required=True)
    active = fields.Boolean(string="是否可用", default=True)
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("developing", "开发中"),
            ("test", "测试"),
            ("normal", "正式"),
            ("paused", "停用"),
        ],
        string="应用状态",
        default="draft",
    )
    weapp_id = fields.Many2one(
        "wechat.weapp.config", string="微信小程序", ondelete="set null"
    )

    ver_ids = fields.One2many("galaxy.qq.app.ver", "app_id", string="版本")
    last_version = fields.Many2one(
        "galaxy.qq.app.ver", compute="_compute_last_version", string="最新版本")
    qq_user_ids = fields.One2many("galaxy.qq.users", "app_id", string="用户")
    # allow_list
    # deny_list
    description = fields.Text(string="描述")

    def _temporary_login_name(self):
        return f"{str(time.time())}@{str(random.randrange(0, 1000))}.com"

    @api.onchange("ver_ids")
    def _compute_last_version(self):
        for rec in self:
            if rec.ver_ids:
                rec.last_version = rec.ver_ids[0]
            else:
                rec.last_version = False

    def get_access_key(
        self, sid, mobile=None, email=None, platform_os=None, phone_model=None
    ):
        self.ensure_one()

        login_with = mobile or (email and email.lower())
        app_user_data = {
            "app_id": self.id,
            "user_id": self.user_id.id,
            "mobile" if mobile else "email": login_with,
        }
        if mobile:
            app_user = self.env["galaxy.qq.users"].sudo().search([
                ("app_id", "=", self.id),
                ("mobile", "=", login_with),
            ], limit=1)
        elif email:
            app_user = self.env["galaxy.qq.users"].sudo().search([
                ("app_id", "=", self.id),
                ("email", "=", login_with),
            ], limit=1)
        else:
            app_user = False
            login_with = self._temporary_login_name()
            app_user_data.update(
                {
                    "email": login_with,
                }
            )

        if not app_user or not app_user.id:
            cache_base = retrieve_cache_base(self.env, "TOKEN-CACHE")
            with cache_base.redis_db.connection_open() as db:
                debounce = db.get(f"debounce_{login_with}")
                if debounce:
                    raise UserError(
                        _("请勿频繁操作，请稍后再试！")
                    )
                else:
                    db.setex(
                        name=f"debounce_{login_with}",
                        value="debounce",
                        time=DEBOUNCE,
                    )
                    app_user = self.env["galaxy.qq.users"].sudo().create(app_user_data)

        return app_user.get_access_key(sid, login_with, platform_os, phone_model)


class GalaxyQqAppVer(models.Model):
    _name = "galaxy.qq.app.ver"
    _inherit = ["uuid.short.mixin"]
    _description = "青钱闪付APP版本"
    _order = "create_date desc"
    _rec_name = "ver"

    app_id = fields.Many2one(
        "galaxy.qq.app",
        string="应用",
        index=True,
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    ver = fields.Char(string="版本号", required=True)
    ver_secret = fields.Char(
        string="版本密钥",
        required=True,
        default=lambda self: self.short_uuid4(length=32),
    )
    force_update = fields.Boolean(string="强制更新", default=False)
    #download_url = fields.Char(string="下载地址")
    ios_download_url = fields.Char(string="IOS下载地址", default="https://apps.apple.com/cn/app/fodsports-connect/id6738982430")
    android_download_url = fields.Char(string="Android下载地址")
    description = fields.Text(string="描述")
