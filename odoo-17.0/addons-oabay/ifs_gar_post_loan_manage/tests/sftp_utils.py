#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""SFTP 公共工具方法。"""

from __future__ import annotations

import os
import posixpath
import time
from dataclasses import dataclass

import paramiko


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class SftpConfig:
    host: str = _env("SFTP_HOST", "")
    port: int = int(_env("SFTP_PORT", "22"))
    username: str = _env("SFTP_USERNAME", "")
    password: str = _env("SFTP_PASSWORD", "")
    base_dir: str = _env("SFTP_BASE_DIR", "/upload")

    def __post_init__(self) -> None:
        if not self.host:
            raise RuntimeError("缺少环境变量 SFTP_HOST。")
        if not self.username:
            raise RuntimeError("缺少环境变量 SFTP_USERNAME。")
        if not self.password:
            raise RuntimeError("缺少环境变量 SFTP_PASSWORD。")


def _mkdirs(sftp, remote_dir: str) -> None:
    """递归创建远程目录。"""
    normalized = posixpath.normpath(remote_dir)
    parts = normalized.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = f"{current}/{part}"
        try:
            sftp.stat(current)
        except IOError:
            sftp.mkdir(current)


def upload_contract_attachment(
    local_path: str,
    contract_no: str,
    remote_filename: str,
    config: SftpConfig | None = None,
) -> str:
    """上传合同附件到 SFTP，返回远程文件路径。"""
    if not os.path.isfile(local_path):
        raise FileNotFoundError(f"本地附件不存在: {local_path}")

    cfg = config or SftpConfig()
    date_path = time.strftime("%Y%m%d")
    remote_dir = posixpath.join(cfg.base_dir, date_path, contract_no)
    remote_path = posixpath.join(remote_dir, remote_filename)

    transport = paramiko.Transport((cfg.host, cfg.port))
    try:
        transport.connect(username=cfg.username, password=cfg.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        _mkdirs(sftp, remote_dir)
        sftp.put(local_path, remote_path)
    finally:
        transport.close()

    return remote_path
