#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
采购方邀请 openapi 接口 HttpCase 单元测试

覆盖接口：
1) GET  /openapi/token                        （获取 access_token / api_key）
2) POST /openapi/merchant/invite/init         （初始化邀请）
3) POST /openapi/merchant/invite/send         （发送邀请）

设计要点（参考 https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html）：
- 同时支持两种运行模式：
    A) Odoo 测试运行器（推荐）
       ./odoo-bin -c debian/odoo.conf -d <db> -u ifs_gar_invite \\
           --test-tags 'external/ifs_gar_invite' --stop-after-init
    B) 作为普通 Python 脚本直接运行（本地要有已启动的 Odoo 实例，默认 8069）
       python3 addons-oabay/ifs_gar_invite/tests/test_openapi_invite_api.py
- 基类：能导入 odoo 时继承 HttpCase（可用 self.env / tag），否则降级到 unittest.TestCase。
- HTTP 客户端：始终使用 requests.Session，不依赖 HttpCase 的 url_open / opener，
  这样两种运行模式下行为一致，也能在本地直跑时命中已在 8069 运行的 Odoo。
- @tagged('-standard', 'external', 'post_install', '-at_install')：把用例从默认
  --test-enable 的 standard 集里摘出去，需要时 --test-tags external 选入。
- base_url 来源优先级：
    1. 环境变量 INVITE_TEST_BASE_URL
    2. Odoo 运行期 config['http_port']（通过 --test-enable 由 Odoo 自动填）
    3. 默认 http://127.0.0.1:8069
- 所有关键参数都支持 INVITE_TEST_* 环境变量覆盖，方便本地 / CI 切换。

注意：init / send 会调用下游真实金证签约接口，会产生真实脏数据，不要在生产库里跑。
"""

from __future__ import annotations

import base64
import json
import logging
import os
import unittest
from dataclasses import dataclass, field
from typing import Any

import requests

try:
    from odoo.tests import HttpCase as _OdooHttpCase
    from odoo.tests import tagged
    from odoo.tools import config as _odoo_config
    _HAS_ODOO = True
except ImportError:
    _HAS_ODOO = False
    _odoo_config = None

    class _OdooHttpCase(unittest.TestCase):
        """Fallback：脱离 Odoo 环境直接运行时用普通 unittest.TestCase。"""

    def tagged(*_args, **_kwargs):
        def _wrap(cls):
            return cls
        return _wrap


_logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


def _resolve_base_url() -> str:
    """base_url 解析优先级：环境变量 > Odoo http_port > localhost:8069。"""
    explicit = os.environ.get("INVITE_TEST_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    if _HAS_ODOO and _odoo_config is not None:
        port = _odoo_config.get("http_port")
        if port:
            return f"http://127.0.0.1:{port}"
    return "http://127.0.0.1:8069"
    # return "https://ceshi.oabay.com"


def build_logo_base64(logo_path: str = "") -> str:
    logo_path = logo_path or _env("INVITE_TEST_LOGO_PATH", "/home/inoryzzz/图片/blank.jpg")
    try:
        with open(logo_path, "rb") as fp:
            return base64.b64encode(fp.read()).decode("utf-8")
    except FileNotFoundError:
        return ""


@dataclass
class ApiConfig:
    appid: str = _env("INVITE_TEST_APPID", "goHUXWhTkeIrnAk65O")
    secret: str = _env("INVITE_TEST_SECRET", "LV4nGSn8NKLrlQN1wOmStHxnkxlK5Bjb")
    grant_type: str = "client_credential"

    timeout: int = 300

    init_params: dict[str, Any] = field(
        default_factory=lambda: {
            "supplier_code": _env("INVITE_TEST_SUPPLIER_CODE", "3000001"),
            "factor_code": _env("INVITE_TEST_FACTOR_CODE", "9000001"),
            "company_name": _env("INVITE_TEST_COMPANY_NAME", "阿里巴巴（中国）有限公司"),
            "company_registry": _env("INVITE_TEST_COMPANY_REGISTRY", "91330100799655058B"),
            "business_address": _env("INVITE_TEST_BUSINESS_ADDRESS", "西大望路甲12号(国家广告产业园区)B座6层"),
            "email": _env("INVITE_TEST_EMAIL", "shizhou.fsz@alibaba-inc.com"),
            "phone": _env("INVITE_TEST_PHONE", "0571-85022088"),
            "logo": "",
        }
    )

    send_params: dict[str, Any] = field(
        default_factory=lambda: {
            "supplier_code": _env("INVITE_TEST_SUPPLIER_CODE", "3000001"),
            "factor_code": _env("INVITE_TEST_FACTOR_CODE", "9000001"),
            "invite_merchant_id": 0,
            "ifs_company_id": 0,
            "mobile_phone": _env("INVITE_TEST_PHONE", "0571-85022088"),
            "work_email": _env("INVITE_TEST_EMAIL", "shizhou.fsz@alibaba-inc.com"),
            "notes": "API unittest",
        }
    )


CONFIG = ApiConfig()


@tagged("-standard", "external", "post_install", "-at_install")
class TestInviteOpenapiFlow(_OdooHttpCase):
    """采购方邀请 openapi 完整链路：token → init → send。"""

    config: ApiConfig = CONFIG

    @classmethod
    def base_url(cls) -> str:
        """覆盖父类实现：既兼容 --test-enable 启动的 Odoo http 端口，
        也兼容本地 `python3 xx.py` 直跑（默认 localhost:8069）。"""
        return _resolve_base_url()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if _HAS_ODOO and hasattr(cls, "env"):
            app = cls.env["galaxy.open.api.app"].sudo().search(
                [("app_id", "=", cls.config.appid)], limit=1,
            )
            if not app:
                raise unittest.SkipTest(
                    f"测试库中未找到 openapi 应用 app_id={cls.config.appid}；"
                    "可通过环境变量 INVITE_TEST_APPID / INVITE_TEST_SECRET 指定库中已存在的应用。"
                )

        if not cls.config.init_params.get("logo"):
            cls.config.init_params["logo"] = build_logo_base64()

        _logger.info("base_url = %s", cls.base_url())

    def setUp(self):
        super().setUp()
        self._session = requests.Session()

    # ---------------- HTTP 小工具 ----------------

    def _pretty(self, title: str, data: Any) -> None:
        _logger.info("===== %s =====\n%s", title, json.dumps(data, ensure_ascii=False, indent=2))

    def _absolute_url(self, path: str) -> str:
        return f"{self.base_url()}{path}"

    def _get(self, path: str, params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> Any:
        resp = self._session.get(
            self._absolute_url(path),
            params=params,
            headers=headers,
            timeout=self.config.timeout,
        )
        self.assertEqual(resp.status_code, 200,
                         msg=f"GET {path} HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    def _post_jsonrpc(self, path: str, params: dict[str, Any],
                      headers: dict[str, str] | None = None) -> dict[str, Any]:
        headers = {**(headers or {}), "Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 3154,
        }
        resp = self._session.post(
            self._absolute_url(path),
            json=payload,
            headers=headers,
            timeout=self.config.timeout,
        )
        self.assertEqual(resp.status_code, 200,
                         msg=f"POST {path} HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    def _openapi_headers(self) -> dict[str, str]:
        data = self._get(
            "/openapi/token",
            params={
                "grant_type": self.config.grant_type,
                "appid": self.config.appid,
                "secret": self.config.secret,
            },
        )
        self._pretty("TOKEN RESPONSE", data)
        access_token = data.get("access_token")
        api_key = data.get("api_key")
        self.assertTrue(access_token, msg=f"未获取到 access_token: {data}")
        self.assertTrue(api_key, msg=f"未获取到 api_key: {data}")
        return {
            "X-GALAXY-ACCESS-TOKEN": access_token,
            "X-GALAXY-API-KEY": api_key,
        }

    # ---------------- 业务步骤 ----------------

    def _assert_business_ok(self, resp: dict[str, Any], label: str) -> dict[str, Any]:
        self.assertNotIn("error", resp, msg=f"{label} 接口层错误: {resp}")
        result = resp.get("result")
        self.assertIsInstance(result, dict, msg=f"{label} result 非 dict: {resp}")
        self.assertFalse(result.get("error_msg"),
                         msg=f"{label} 业务失败: {result.get('error_msg')}")
        return result

    def _call_init(self, headers: dict[str, str]) -> dict[str, Any]:
        params = dict(self.config.init_params)
        if not params.get("logo"):
            params["logo"] = build_logo_base64()
        resp = self._post_jsonrpc("/openapi/merchant/invite/init", params, headers=headers)
        self._pretty("INIT RESPONSE", resp)
        result = self._assert_business_ok(resp, "init")
        self.assertTrue(result.get("invite_merchant_id"),
                        msg=f"init 返回缺少 invite_merchant_id: {result}")
        self.assertTrue(result.get("ifs_company_id"),
                        msg=f"init 返回缺少 ifs_company_id: {result}")
        return result

    def _call_send(self, headers: dict[str, str],
                   invite_merchant_id: int, ifs_company_id: int) -> dict[str, Any]:
        params = dict(self.config.send_params)
        params["invite_merchant_id"] = invite_merchant_id
        params["ifs_company_id"] = ifs_company_id
        resp = self._post_jsonrpc("/openapi/merchant/invite/send", params, headers=headers)
        self._pretty("SEND RESPONSE", resp)
        return self._assert_business_ok(resp, "send")

    # ---------------- 测试用例 ----------------

    def test_01_fetch_token(self):
        """/openapi/token: 能正确拿到 access_token 和 api_key"""
        headers = self._openapi_headers()
        self.assertIn("X-GALAXY-ACCESS-TOKEN", headers)
        self.assertIn("X-GALAXY-API-KEY", headers)

    def test_02_invite_init(self):
        """/openapi/merchant/invite/init: 初始化成功，返回 invite_merchant_id / ifs_company_id"""
        headers = self._openapi_headers()
        self._call_init(headers)

    def test_03_invite_full_flow(self):
        """init + send 完整链路：用 init 返回的 id 驱动 send，最终都不报错"""
        headers = self._openapi_headers()
        init_result = self._call_init(headers)
        self._call_send(
            headers,
            invite_merchant_id=init_result["invite_merchant_id"],
            ifs_company_id=init_result["ifs_company_id"],
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    unittest.main(verbosity=2)
