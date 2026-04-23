#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动补全联系人接口联调测试

覆盖接口：
1) /autocomplete/contact            (auth="user",    内部 Session 登录)
2) /openapi/autocomplete/contact    (auth="openapi", X-GALAXY-ACCESS-TOKEN + X-GALAXY-API-KEY)

通过条件：
- 固定关键字 keyword = "91321200608775189J"
- 接口返回的 result 为非空字典 -> 通过

使用方式：
- 直接运行（默认读取脚本内 CONFIG）:
    python3 addons-oabay/ifs_partner_autocomplete/tests/test_openapi.py
- 通过 unittest:
    python3 -m unittest addons-oabay.ifs_partner_autocomplete.tests.test_openapi -v

注意：
- 需要对应的 Odoo 实例处于运行状态（默认 http://127.0.0.1:8069），且能够访问下游天眼查。
- 该用例依赖真实第三方接口，不适合在 CI 默认测试集里跑，因此用 @tagged('-standard', 'external')
  将其从 Odoo 的默认 --test-enable 测试集里排除；需要时用 --test-tags external 显式开启。
"""

from __future__ import annotations

import json
import logging
import unittest
from dataclasses import dataclass
from typing import Any

import requests

try:
    from odoo.tests.common import tagged
except ImportError:
    def tagged(*_args, **_kwargs):
        def _wrap(cls):
            return cls
        return _wrap


_logger = logging.getLogger(__name__)

KEYWORD = "91321200608775189J"


@dataclass
class ApiConfig:
    base_url: str = "http://127.0.0.1:8069"

    db: str = "17-oabay-ceshi"
    login: str = "admin"
    password: str = "admin"

    appid: str = "goHUXWhTkeIrnAk65O"
    secret: str = "LV4nGSn8NKLrlQN1wOmStHxnkxlK5Bjb"
    grant_type: str = "client_credential"
    access_token: str = ""
    api_key: str = ""

    timeout: int = 300


CONFIG = ApiConfig()


def _pretty(title: str, data: Any) -> None:
    _logger.info("===== %s =====\n%s", title, json.dumps(data, ensure_ascii=False, indent=2))


def post_jsonrpc(
    session: requests.Session,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": 1,
    }
    resp = session.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_openapi_credentials(
    session: requests.Session, config: ApiConfig
) -> tuple[str, str]:
    if config.access_token and config.api_key:
        return config.access_token, config.api_key

    resp = session.get(
        f"{config.base_url}/openapi/token",
        params={
            "grant_type": config.grant_type,
            "appid": config.appid,
            "secret": config.secret,
        },
        timeout=config.timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    _pretty("TOKEN RESPONSE", data)

    access_token = data.get("access_token") or config.access_token
    api_key = data.get("api_key") or config.api_key
    if not access_token:
        raise RuntimeError("未获取到 access_token，请检查 appid/secret")
    if not api_key:
        raise RuntimeError("未获取到 api_key，请检查 openapi 配置")
    return access_token, api_key


def get_openapi_session_headers(
    config: ApiConfig = CONFIG,
) -> tuple[requests.Session, dict[str, str]]:
    session = requests.Session()
    access_token, api_key = fetch_openapi_credentials(session, config)
    headers = {
        "Content-Type": "application/json",
        "X-GALAXY-ACCESS-TOKEN": access_token,
        "X-GALAXY-API-KEY": api_key,
    }
    return session, headers


def get_user_session_headers(
    config: ApiConfig = CONFIG,
) -> tuple[requests.Session, dict[str, str]]:
    """内部用户登录：调用 /web/session/authenticate 后，requests.Session 会保留 Cookie。"""
    session = requests.Session()
    url = f"{config.base_url}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": config.db,
            "login": config.login,
            "password": config.password,
        },
        "id": 1,
    }
    resp = session.post(url, json=payload, timeout=config.timeout)
    resp.raise_for_status()
    data = resp.json()
    _pretty("LOGIN RESPONSE", data)
    if "error" in data:
        raise RuntimeError(f"登录 Odoo 失败: {data['error']}")
    if not (data.get("result") or {}).get("uid"):
        raise RuntimeError(f"登录 Odoo 失败（未返回 uid）: {data}")
    headers = {"Content-Type": "application/json"}
    return session, headers


def call_autocomplete_contact(
    session: requests.Session,
    config: ApiConfig,
    headers: dict[str, str],
    url_path: str,
    keyword: str = KEYWORD,
) -> dict[str, Any]:
    url = f"{config.base_url}{url_path}"
    resp = post_jsonrpc(session, url, headers, {"keyword": keyword}, config.timeout)
    _pretty(f"AUTOCOMPLETE CONTACT {url_path}", resp)
    return resp


@tagged("-standard", "external")
class AutocompleteContactApiTest(unittest.TestCase):
    """联调真实 Odoo 与下游天眼查的接口测试。"""

    config: ApiConfig = CONFIG
    keyword: str = KEYWORD

    def _assert_non_empty_result(self, resp_json: dict[str, Any]) -> dict[str, Any]:
        self.assertNotIn("error", resp_json, msg=f"接口返回错误: {resp_json}")
        result = resp_json.get("result")
        self.assertIsInstance(result, dict, msg=f"result 非 dict: {resp_json}")
        self.assertTrue(result, msg=f"result 为空字典（判定为失败）: {resp_json}")
        return result

    def test_autocomplete_contact_as_user(self):
        """/autocomplete/contact 走内部用户 Session 登录"""
        session, headers = get_user_session_headers(self.config)
        resp = call_autocomplete_contact(
            session, self.config, headers,
            url_path="/autocomplete/contact",
            keyword=self.keyword,
        )
        self._assert_non_empty_result(resp)

    def test_openapi_autocomplete_contact(self):
        """/openapi/autocomplete/contact 走 openapi access_token + api_key"""
        session, headers = get_openapi_session_headers(self.config)
        resp = call_autocomplete_contact(
            session, self.config, headers,
            url_path="/openapi/autocomplete/contact",
            keyword=self.keyword,
        )
        self._assert_non_empty_result(resp)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    unittest.main(verbosity=2)
