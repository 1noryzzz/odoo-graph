#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""昊悦征信 - 担保信息接口联调脚本。

说明：
1) 该文件独立于基础信息脚本，避免改动现有文件；
2) 复用当前加密方式（AES + Base64 key/iv）；
3) 使用固定样例参数优先打通接口调用。
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
    CompAdvFlag,
    Currency,
    FiveCategory,
    GuaranteeAcctType,
    GuaranteeBusinessDetailLine,
    GuaranteeBusinessLine,
    GuaranteeMode,
    IdType,
    LiabilityAcctStatus,
    OtherRepaymentGuaranteeWay,
    RelatedRepayObligorInfoldType,
    RepayObligorType,
    WartySign,
)

_logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class ApiConfig:
    """调试配置。"""

    base_url: str = _env("CREDIT_TEST_BASE_URL", "").rstrip("/")
    endpoint: str = "/third/party/guarantee"
    timeout: int = int(_env("CREDIT_TEST_TIMEOUT", "60"))

    org_id: str = _env("CREDIT_TEST_ORG_ID", "YB_FALLING")
    product_code: str = _env("CREDIT_TEST_PRODUCT_CODE", "YB_FALLING")

    aes_key: str = _env("CREDIT_TEST_AES_KEY", "")
    aes_iv_b64: str = _env("CREDIT_TEST_AES_IV_B64", "")

    def __post_init__(self) -> None:
        if not self.base_url:
            raise RuntimeError("缺少环境变量 CREDIT_TEST_BASE_URL。")
        if not self.aes_key:
            raise RuntimeError("缺少环境变量 CREDIT_TEST_AES_KEY。")
        if not self.aes_iv_b64:
            raise RuntimeError("缺少环境变量 CREDIT_TEST_AES_IV_B64。")


CONFIG = ApiConfig()


def _pretty(title: str, data: Any) -> None:
    _logger.info("===== %s =====\n%s", title, json.dumps(data, ensure_ascii=False, indent=2))


def build_guarantee_item() -> dict[str, Any]:
    """按文档样例构造单条担保信息。"""
    return {
        "thirdSeq": "LOAN_THIRD_001",
        "infoUpDate": "2026-04-03",
        "acctType": GuaranteeAcctType.FINANCING_GUARANTEE,
        "acctNo": "GUAR_ACCT_CONTRACT_001",
        "custName": "张三",
        "idType": IdType.RESIDENT_ID,
        "idNo": "110101199001011234",
        "busiLines": GuaranteeBusinessLine.FINANCING_GUARANTEE,
        "busiDtlLines": GuaranteeBusinessDetailLine.LOAN_GUARANTEE,
        "openDate": "2026-01-15",
        "acctCredLine": 50000,
        "loanCcy": Currency.CNY,
        "dueDate": "2027-01-15",
        "guraMode": GuaranteeMode.MORTGAGE,
        "othRepyGuraWay": OtherRepaymentGuaranteeWay.NONE,
        "secDep": "0",
        "ctrctTxtCd": "GUAR_TEXT_2026_001",
        "releRepayObligor": [
            {
                "infoIdType": RelatedRepayObligorInfoldType.NATURAL_PERSON,
                "arlpName": "王五",
                "arlpCertType": IdType.RESIDENT_ID,
                "arlpCertNum": "110101198801011234",
                "arlpType": RepayObligorType.COUNTER_GUARANTOR,
                "arlpAmt": "50000",
                "wartySign": WartySign.SINGLE_OR_SPLIT,
                "maxGuarMcc": "11000000000001GUAR_CONTRACT_0001",
            }
        ],
        "liabInfo": {
            "acctStatus": LiabilityAcctStatus.NORMAL,
            "loanAmt": "48000",
            "repayPrd": "2026-04-03",
            "fiveCate": FiveCategory.NORMAL,
            "fiveCateAdjDate": "2026-04-01",
            "riskEx": "48000",
            "compAdvFlag": CompAdvFlag.NO,
            "closeDate": None,
        },
    }


def build_inner_payload() -> dict[str, Any]:
    return {
        "seqNo": f"SEQ{time.strftime('%Y%m%d%H%M%S')}",
        "dataSize": "1",
        "itemList": [build_guarantee_item()],
    }


def build_outer_payload(config: ApiConfig) -> dict[str, Any]:
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


def post_guarantee_info(config: ApiConfig, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{config.base_url}{config.endpoint}"
    resp = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=config.timeout,
    )
    resp.raise_for_status()
    return resp.json()


class TestGuaranteeInfoApi(unittest.TestCase):
    """担保信息接口最小联调测试。"""

    def test_guarantee_info_request(self):
        payload = build_outer_payload(CONFIG)
        _pretty("GUARANTEE REQUEST PAYLOAD", payload)

        response_json = post_guarantee_info(CONFIG, payload)
        _pretty("GUARANTEE RESPONSE RAW", response_json)

        self.assertIsInstance(response_json, dict, msg=f"返回非 JSON 对象: {response_json}")
        self.assertIn("retCode", response_json, msg=f"返回缺少 retCode: {response_json}")
        self.assertIn("retMsg", response_json, msg=f"返回缺少 retMsg: {response_json}")

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
            _pretty("GUARANTEE RESPONSE DATA DECRYPTED", parsed_decrypted_data)

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
