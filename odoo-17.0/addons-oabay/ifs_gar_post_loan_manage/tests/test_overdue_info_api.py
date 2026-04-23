#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""昊悦征信 - 逾期催收接口联调脚本。"""

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
from dotenv import load_dotenv

from crypto_utils import decrypt, encrypt
from credit_enums import (
    AssetTrandFlag,
    Currency,
    FiveCategory,
    FundSource,
    IdType,
    InitRepayStatus,
    ImagingDocCode,
    LoanForm,
    OrigDebtCategory,
    OthRepyGuarWay,
    OverdueAcctStatus,
    OverdueAcctType,
    OverdueBusinessDetailLine,
    OverdueBusinessLine,
    OverdueGuarMode,
    RepayFrequency,
    RepayMode,
    RepayStatus,
)
from sftp_utils import upload_contract_attachment

load_dotenv()

_logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class ApiConfig:
    base_url: str = _env("CREDIT_TEST_BASE_URL", "").rstrip("/")
    endpoint: str = "/third/party/overdue"
    timeout: int = int(_env("CREDIT_TEST_TIMEOUT", "60"))

    org_id: str = _env("CREDIT_TEST_ORG_ID", "YB_FALLING")
    product_code: str = _env("CREDIT_TEST_PRODUCT_CODE", "YB_FALLING")

    aes_key: str = _env("CREDIT_TEST_AES_KEY", "")
    aes_iv_b64: str = _env("CREDIT_TEST_AES_IV_B64", "")

    # 可选：本地附件路径，存在则先上传 SFTP 并回填 docFile。
    attachment_local_path: str = _env("OVERDUE_TEST_ATTACHMENT_LOCAL_PATH", "/home/inoryzzz/下载/昊悦征信上报-接口文档.pdf")

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


def _build_doc_file_path(contract_no: str, doc_code: ImagingDocCode = ImagingDocCode.OVERDUE_NOTIFICATION, local_path: str | None = None) -> str:
    """优先上传本地附件到 SFTP，失败则返回文档样例路径。
    
    Args:
        contract_no: 合同编号
        doc_code: 影像资料码值
    Returns:
        str: 文档文件路径
    """
    filename = f"{ImagingDocCode.filename_by_code(doc_code.value)}.pdf"
    uploaded = upload_contract_attachment(
        local_path=local_path or CONFIG.attachment_local_path,
        contract_no=contract_no,
        remote_filename=filename,
    )
    return uploaded


def build_overdue_item() -> dict[str, Any]:
    contract_no = "HT202505310001"
    doc_file = _build_doc_file_path(contract_no)

    return {
        "thirdSeq": "LOAN_THIRD_001",
        "infoUpDate": "2026-04-03",
        "acctNo": "LOAN_ACCT_001",
        "acctType": OverdueAcctType.NON_REVOLVING_LOAN,
        "name": "张三",
        "idType": IdType.RESIDENT_ID,
        "idNum": "110101199001011234",
        "busiLines": OverdueBusinessLine.LOAN,
        "busiDtlLines": OverdueBusinessDetailLine.OTHER_PERSONAL_CONSUMPTION_LOAN,
        "openDate": "2025-06-01",
        "loanCcy": Currency.CNY,
        "acctCredLine": None,
        "loanAmt": 50000,
        "flag": "0",
        "dueDate": "2026-05-31",
        "repayMode": RepayMode.INSTALLMENT_EQUAL_PI,
        "repayFreqcy": RepayFrequency.MONTH,
        "repayPrd": 12,
        "applyBusiDist": "110105",
        "guarMode": OverdueGuarMode.ASSURANCE,
        "othRepyGuarWay": OthRepyGuarWay.NONE,
        "assetTrandFlag": AssetTrandFlag.NO,
        "fundSou": FundSource.SELF_OPERATED,
        "loanForm": LoanForm.NEW_ADD,
        "creditId": "NULL",
        "firstHouLoanFlag": None,
        "loanConCode": None,
        "initCredInfo": {
            "initCredName": "某某银行股份有限公司北京分行",
            "initCredOrgNm": "91110000MA01234567",
            "origDbtCate": OrigDebtCategory.PERFORMING,
            "initRpySts": InitRepayStatus.DEFAULT,
        },
        "nonMonPerf": {
            "acctStatus": OverdueAcctStatus.OVERDUE,
            "acctBal": 1200.5,
            "fiveCate": FiveCategory.ATTENTION,
            "fiveCateAdjDate": "2026-03-25",
            "remRepPrd": 8,
            "rpystatus": RepayStatus.OVERDUE,
            "overdPrd": 2,
            "totOverd": 1200.5,
            "latRpyAmt": 0,
            "latRpyDate": "2026-02-10",
            "closeDate": None,
        },
        "iDocList": [
            {
                "docFile": doc_file,
                "docCde": ImagingDocCode.OVERDUE_NOTIFICATION,
                "docName": os.path.basename(doc_file),
                "contractNo": contract_no,
            }
        ],
    }


def build_inner_payload() -> dict[str, Any]:
    return {
        "seqNo": f"SEQ{time.strftime('%Y%m%d%H%M%S')}",
        "dataSize": "1",
        "itemList": [build_overdue_item()],
    }


def build_outer_payload(config: ApiConfig) -> dict[str, Any]:
    inner_payload = build_inner_payload()
    _pretty("OVERDUE INNER PAYLOAD before encrypt", inner_payload)
    data_plain = json.dumps(inner_payload, ensure_ascii=False)
    data_field = encrypt(data_plain, config.aes_key, config.aes_iv_b64)
    return {
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "orgId": config.org_id,
        "productCode": config.product_code,
        "data": data_field,
    }


def post_overdue_info(config: ApiConfig, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{config.base_url}{config.endpoint}"
    resp = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=config.timeout,
    )
    resp.raise_for_status()
    return resp.json()


class TestOverdueInfoApi(unittest.TestCase):
    """逾期催收接口最小联调测试。"""

    def test_overdue_info_request(self):
        payload = build_outer_payload(CONFIG)
        _pretty("OVERDUE REQUEST PAYLOAD", payload)

        response_json = post_overdue_info(CONFIG, payload)
        _pretty("OVERDUE RESPONSE RAW", response_json)

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
            _pretty("OVERDUE RESPONSE DATA DECRYPTED", parsed_decrypted_data)

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
