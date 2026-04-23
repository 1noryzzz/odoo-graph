#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""昊悦征信 - 基础信息接口联调脚本。

当前阶段目标：
1) 固定参数验证接口可请求成功；
2) 请求按 AES 规则加密发送；
3) 响应 data 按 AES 规则解密打印。
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
import unittest
from dataclasses import dataclass
from typing import Any

import requests

from crypto_utils import decrypt, encrypt
from credit_enums import (
    Caste,
    CompanyType,
    Country,
    Degree,
    Duty,
    Education,
    EmploymentStatus,
    IdType,
    IndustryType,
    LiveInfo,
    MaritalStatus,
    Position,
    Sex,
)
from dotenv import load_dotenv
load_dotenv()

_logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class ApiConfig:
    """调试配置。"""

    # 按计划保持空占位，运行时通过环境变量传入。
    base_url: str = _env("CREDIT_TEST_BASE_URL", "").rstrip("/")
    endpoint: str = "/third/party/credit"
    timeout: int = int(_env("CREDIT_TEST_TIMEOUT", "60"))

    # 文档当前固定值（后续可改）
    org_id: str = "YB_FALLING"
    product_code: str = "YB_FALLING"

    # 加解密参数（必须）
    aes_key: str = _env("CREDIT_TEST_AES_KEY", "")
    aes_iv_b64: str = _env("CREDIT_TEST_AES_IV_B64", "")

    def __post_init__(self) -> None:
        if not self.aes_key:
            raise RuntimeError("缺少环境变量 CREDIT_TEST_AES_KEY。")
        if not self.aes_iv_b64:
            raise RuntimeError("缺少环境变量 CREDIT_TEST_AES_IV_B64。")


CONFIG = ApiConfig()


def _pretty(title: str, data: Any) -> None:
    _logger.info("===== %s =====\n%s", title, json.dumps(data, ensure_ascii=False, indent=2))


def build_credit_item() -> dict[str, Any]:
    """构造单条基础信息样例（固定值）。"""
    return {
        "thirdSeq": "LOAN_THIRD_001",
        "infoUpDate": "2026-04-03",
        "acctNo": "ACCT_CONTRACT_NO_202604030001",
        "userType": "0",
        "custName": "张三",
        "idType": IdType.RESIDENT_ID,
        "idNo": "110101199001011234",
        "regArea": "110105",
        "regAddr": "北京市朝阳区某某路1号",
        "indivSex": Sex.MALE,
        "country": Country.CHINA,
        "indivMarital": MaritalStatus.MARRIED,
        "spouseName": "李四",
        "spouseIdType": IdType.RESIDENT_ID,
        "spouseIdNum": "110101199002021234",
        "spouseTel": "13800138001",
        "spouseCmpyName": "某某科技有限公司",
        "indivEdu": Education.BACHELOR,
        "eduDegree": Degree.BACHELOR,
        "indivMobile": "13800138000",
        "liveInfo": LiveInfo.OTHER,
        "liveArea": "110105",
        "liveAddr": "北京市朝阳区某某小区1号楼101",
        "empStatus": EmploymentStatus.EMPLOYED,
        "indivEmpName": "某某科技有限公司",
        "indivEmpTel": "010-12345678",
        "indivEmpArea": "110105",
        "indivEmpAddr": "北京市朝阳区某某产业园A座",
        "indivPc": "100020",
        "indivType": CompanyType.PRIVATE,
        "position": Position.OFFICE_STAFF,
        "induInvol": IndustryType.EDUCATION,
        "duty": Duty.STAFF,
        "caste": Caste.NONE,
        "workStartDate": "2018",
        "mailAddr": "北京市朝阳区某某路收",
        "mailPc": "100020",
    }


def build_inner_payload() -> dict[str, Any]:
    """构造 data 解密前明文对象（当前阶段不加密）。"""
    credit_item = build_credit_item()
    return {
        "seqNo": f"SEQ{time.strftime('%Y%m%d%H%M%S')}",
        "dataSize": "1",
        "itemList": [credit_item],
    }


def build_outer_payload(config: ApiConfig) -> dict[str, Any]:
    """构造接口通用外层报文。"""
    inner_payload = build_inner_payload()
    _pretty("INNER PAYLOAD before encrypt", inner_payload)
    data_plain = json.dumps(inner_payload, ensure_ascii=False)
    data_field = encrypt(data_plain, config.aes_key, config.aes_iv_b64)
    return {
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "orgId": config.org_id,
        "productCode": config.product_code,
        "data": data_field,
    }


def validate_conditional_required(payload: dict[str, Any]) -> list[str]:
    """根据文档做提醒型校验（不阻塞）。"""
    warnings: list[str] = []
    inner_payload = build_inner_payload()
    credit_items = inner_payload.get("itemList") or []
    if not credit_items:
        warnings.append("itemList 为空，文档要求至少一条基础信息。")
        return warnings

    credit = credit_items[0]
    marital = credit.get("indivMarital")
    if marital in {"20", "21", "01", "0"}:
        for field in ("spouseName", "spouseIdType", "spouseIdNum"):
            if not credit.get(field):
                warnings.append(f"当婚姻状态={marital} 时，字段 {field} 建议必填。")

    if credit.get("empStatus") == EmploymentStatus.EMPLOYED:
        for field in (
            "indivEmpName",
            "indivEmpTel",
            "indivEmpArea",
            "indivEmpAddr",
            "indivPc",
            "indivType",
            "position",
            "induInvol",
            "duty",
            "caste",
            "workStartDate",
        ):
            if not credit.get(field):
                warnings.append(f"当就业状态=在职时，字段 {field} 建议必填。")
    return warnings


def post_basic_info(config: ApiConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if not config.base_url:
        raise RuntimeError(
            "CREDIT_TEST_BASE_URL 为空，请先设置环境变量，例如："
            " export CREDIT_TEST_BASE_URL='http://127.0.0.1:8080'"
        )
    url = f"{config.base_url}{config.endpoint}"
    resp = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=config.timeout,
    )
    resp.raise_for_status()
    return resp.json()


class TestCreditBasicInfoApi(unittest.TestCase):
    """基础信息接口最小联调测试。"""

    def test_credit_basic_info_request(self):
        payload = build_outer_payload(CONFIG)
        warnings = validate_conditional_required(payload)
        if warnings:
            _logger.warning("条件必填提醒:\n- %s", "\n- ".join(warnings))

        _pretty("REQUEST PAYLOAD", payload)
        response_json = post_basic_info(CONFIG, payload)
        _pretty("RESPONSE RAW", response_json)

        if response_json.get("data"):
            decrypted_data = decrypt(
                str(response_json["data"]),
                CONFIG.aes_key,
                CONFIG.aes_iv_b64,
            )
            try:
                parsed_decrypted_data = json.loads(decrypted_data)
            except json.JSONDecodeError:
                parsed_decrypted_data = decrypted_data
            _pretty("RESPONSE DATA DECRYPTED", parsed_decrypted_data)

        # 当前阶段最小成功判定：结构完整，不做响应解密与业务强校验。
        self.assertIsInstance(response_json, dict, msg=f"返回非 JSON 对象: {response_json}")
        self.assertIn("retCode", response_json, msg=f"返回缺少 retCode: {response_json}")
        self.assertIn("retMsg", response_json, msg=f"返回缺少 retMsg: {response_json}")

        if str(response_json.get("retCode")) != "200":
            _logger.warning(
                "接口返回非成功 retCode=%s, retMsg=%s",
                response_json.get("retCode"),
                response_json.get("retMsg"),
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    unittest.main(verbosity=2)
