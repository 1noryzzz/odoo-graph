#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""AES-CBC(PKCS7) 加解密工具。

对齐对方提供的 Java 参考实现：
- 算法: AES/CBC/PKCS5Padding（在 Python 中等价为 PKCS7）
- 编码: UTF-8
- IV: Base64 编码传输
- Key: 字符串 编码输出
"""

from __future__ import annotations

import base64
import os
import secrets

from typing import Final

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from dotenv import load_dotenv

load_dotenv()


AES_BLOCK_SIZE_BITS: Final[int] = 128
IV_SIZE_BYTES: Final[int] = 16
VALID_KEY_LENGTHS: Final[set[int]] = {16, 24, 32}


def generate_aes_key(key_size: int = 16) -> str:
    """生成 AES 密钥并返回 Base64 字符串。"""
    if key_size not in VALID_KEY_LENGTHS:
        raise ValueError(f"非法 AES 密钥长度: {key_size}，仅支持 16/24/32 字节。")
    key = secrets.token_bytes(key_size)
    return base64.b64encode(key).decode("ascii")


def generate_iv() -> str:
    """生成 16 字节 IV，返回 Base64 字符串。"""
    iv = secrets.token_bytes(IV_SIZE_BYTES)
    return base64.b64encode(iv).decode("ascii")


def _build_key_bytes(s_key: str) -> bytes:
    """将字符串 key 编码为原始字节"""
    key_bytes = s_key.encode("utf-8")
    if len(key_bytes) not in VALID_KEY_LENGTHS:
        raise ValueError(f"AES key 长度非法: {len(key_bytes)}，必须是 16/24/32 字节")
    return key_bytes


def encrypt(plain_text: str, s_key: str, iv_parameter: str) -> str:
    """加密字符串，返回 Base64 密文。"""
    try:
        key_bytes = _build_key_bytes(s_key)
        iv_bytes = base64.b64decode(iv_parameter)
        if len(iv_bytes) != IV_SIZE_BYTES:
            raise ValueError("IV Base64 解码后长度必须为 16 字节。")

        padder = padding.PKCS7(AES_BLOCK_SIZE_BITS).padder()
        padded_data = padder.update(plain_text.encode("utf-8")) + padder.finalize()

        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode("ascii")
    except Exception as exc:
        raise RuntimeError(f"加密异常, 待加密串:{plain_text}") from exc


def decrypt(cipher_text: str, s_key: str, iv_parameter: str) -> str:
    """解密 Base64 密文，返回 UTF-8 明文。"""
    try:
        key_bytes = _build_key_bytes(s_key)
        iv_bytes = base64.b64decode(iv_parameter)
        if len(iv_bytes) != IV_SIZE_BYTES:
            raise ValueError("IV Base64 解码后长度必须为 16 字节。")

        encrypted = base64.b64decode(cipher_text)
        cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
        decryptor = cipher.decryptor()
        padded_plain = decryptor.update(encrypted) + decryptor.finalize()

        unpadder = padding.PKCS7(AES_BLOCK_SIZE_BITS).unpadder()
        plain = unpadder.update(padded_plain) + unpadder.finalize()
        return plain.decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"解密异常, 待解密串:{cipher_text}, 错误信息:{exc}") from exc


def debug_decrypt(cipher_text, key, iv):
    import base64
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    cases = [
        ("base64_key", "base64_iv"),
        ("raw_key", "base64_iv"),
        ("base64_key", "raw_iv"),
        ("raw_key", "raw_iv"),
    ]

    for k_mode, iv_mode in cases:
        try:
            if k_mode == "base64_key":
                key_bytes = base64.b64decode(key)
            else:
                key_bytes = key.encode()

            if iv_mode == "base64_iv":
                iv_bytes = base64.b64decode(iv)
            else:
                iv_bytes = iv.encode()

            cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
            decryptor = cipher.decryptor()
            padded = decryptor.update(base64.b64decode(cipher_text)) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            plain = unpadder.update(padded) + unpadder.finalize()

            print("✅ 成功:", k_mode, iv_mode, plain)

        except Exception as e:
            print("❌ 失败:", k_mode, iv_mode, str(e))


if __name__ == '__main__':
    test_data = "N7a/jPFC/SA6dCq77eWC9UgohMT4Nvqkw0b6+aigvjcBS98L/QpSjv+aBJ1oiRmA3/puERdX9pBxfvooO+nmuUecoT3Pu6m/PAbZbrOXi32O4bcTZ+ohVxCTXWFxYK+hTJ+rn+cVyrg4Gv9ovbvc+M5AGRGHYM+QRTLSvHGjG4sUb7DOOXUQHmhQq0XzqpXbsxwTD6YYWRmXxW2OfIzB07cDXLcg2Y1Ju4VDNkr0CoisFI4sjqHgOJUBmctK2oJsxepHVmtDOltR+kXK1Stvw/W63t3wvGjeOYUFd9WmoRhctPvOT7FqYt91FAqwRed9uiPRCUKunp0+NWpRfnCis2kPCRgmCcRVV+PL4VXG2E9ECMJnq97tByFRHkgJ8t6CIaQBulKxG0WdHBwOjH3Wg8jzisl7N1mGhFhg5yoKya57UMFL3BwBXGZeC64WwLLzgv7gWCiZ/OuhPCWR8lLr4Tbrud5beKVyHSxNvZ5mPUjM+zDUcUZnrr+B9aiVfYw7rL4OQqf1gqtQfhgMX2+6T8XX39Q9izsM+Te8l2fdDe9hMHSylr/qbqQNZQwhWNAr7VRNj6e+NAUvB2IgCYX1ayD/aedreUJS2pv9UlfdmEO5G0OGC4u5G+B8AJ680svBkwqcXwy6oe8N1woeIJAkJNHUBOovLKXHMr9V2aCyEdIoT9AwEL6lwuA263UztvdhqfqzX/U0omb7KKyhY18NvSeVQ7hls7iYtP56p9m7/8b5CfmCJBrM+aO2+RE49Gp88NJeSXN6v/gDierTwKxWDLAdgYHwzJ8npibVFhT2CqM87UTqPEz2cMlcOT6rRo7vjaLbqAem49LtBoBMy7gMz/YyKBaoBVsQFvl22qJw2BJrldxNDMJkIFmdLEEuuzfIu8Au1O4u/9K5dTAAc9umV9ppV1nVZ3g6+SSkwM+Upm6BsCASRtuK/+fj12C4LZYIwCPbjJHdjGjkXQC6h3KGMRDhrSOzM0cMDZzHIMvX/0/UKz1ZrxHr5oDh5+9li5+w2iGpxleNo3kjEy8ISkZvcyYMNZV1zdo0sdJwCJ9TCR/br33j/kRefdnv4C4T/71CCYbvGDLgz8CBgtsszCy/c9T1qXV8NRR0/7TFcF3Yn2pNTMbSXFVMlYmWtskRp+1sP+jQSn6EW05WlF1RHG4II3Ol24cjI4PuaFwkkfnwR5zRi5624MzU7+QS8ULMEXBtV5Ftfi2UQMzHBD6iipCPGz9swd/OhCG5QE+xQKfa/uMBAWvGpm0WEqJLcVQ96oLybRNeYcNPibdF9KFW7FMz/9hmGwr+idU7fu4omhuC1XqOf1B4sIiFeFZhRwVa7NTw+azAHCZ8BpDcwdNoQjKmKr47MI69uOVpc+ZyvynLb2ynIOBRsrGmgCPLvR/QiKPxTy5DNwAnosuWo5nbTBC4Og=="
    aes_key = os.environ.get("CREDIT_TEST_AES_KEY")
    aes_iv_b64 = os.environ.get("CREDIT_TEST_AES_IV_B64")

    # print("解密结果:", decrypt(test_data, aes_key, aes_iv_b64))
    # print("加密结果:", encrypt("测试数据", aes_key, aes_iv_b64))
    # debug_decrypt("xQAkmodtNRk+k7RD635X4Q==", aes_key, aes_iv_b64)
