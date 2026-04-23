# -*- coding: utf-8 -*-

import hashlib
import urllib
import logging
import json
import base64
from Crypto.Cipher import AES

from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)

block_size = AES.block_size


class GalaxyExternalApiAuthBairongAceessToken(models.Model):
    _name = 'galaxy.external.api.auth.bairong.ak'
    _inherit = ['galaxy.external.api.auth']
    _description = '百融AccesToken'

    def _md5hlhex(self, data):
        md5hl = hashlib.md5()
        md5hl.update(data.encode('utf8'))
        return md5hl.hexdigest()

    def do_auth(self, headers=None, query=None, body=None, rargs=None):
        super().do_auth(headers, query, body)

        cfg = self.env['ir.config_parameter'].sudo()
        appkey = cfg.get_param('galaxy.bairong.app.code', '')
        appcode = cfg.get_param('galaxy.bairong.app.key', '')
        appKeyHash = self._md5hlhex(
            cfg.get_param('galaxy.bairong.app.key', ''))

        if body.get('strategy_id'):
            jsonData = json.dumps({
                'id': body.get('idcard'),
                'cell': body.get('mobile'),
                'name': body.get('name'),
                'strategy_id': body.get('strategy_id')
            })
        else:
            jsonData = json.dumps({
                'id': body.get('idcard'),
                'cell': body.get('mobile'),
                'name': body.get('name'),
                'conf_id': body.get('conf_id')
            })
        jsonDataAES = AESCipher().AESEncrypt(
            urllib.parse.quote(jsonData), cfg.get_param('galaxy.bairong.app.key', ''))

        checkCode = ''.join([
            jsonData,
            cfg.get_param('galaxy.bairong.app.code', ''),
            cfg.get_param('galaxy.bairong.app.key', ''),
        ])

        checkCodeHash = self._md5hlhex(checkCode)
        body.clear()
        body.update({
            'appKey': appKeyHash,
            'apiCode': cfg.get_param('galaxy.bairong.app.code', ''),
            'jsonData': jsonDataAES,
            'checkCode': checkCodeHash
        })
        rargs.update({
            'verify': False
        })


class AESCipher:
    # 加密
    def AESEncrypt(self, content, key):
        content = self.PKCS5Padding(content)
        genKey = self.SHA1PRNG(key)
        cipher = AES.new(genKey, AES.MODE_ECB)
        return self.EncodeBase64URLSafeString(cipher.encrypt(content))

    def AESDecrypt(self, enc, key):
        genKey = self.SHA1PRNG(key)
        cipher = AES.new(genKey, AES.MODE_ECB)
        return cipher.decrypt(base64.urlsafe_b64decode(enc.encode('utf-8') + b'=='))

    def SHA1PRNG(self, key):
        signature = hashlib.sha1(key.encode()).digest()
        signature = hashlib.sha1(signature).digest()
        return bytes.fromhex(''.join(['%02x' % i for i in signature])[:32])

    def PKCS5Padding(self, plain_text):
        number_of_bytes_to_pad = block_size - \
            len(plain_text.encode("utf-8")) % block_size  # python3
        # number_of_bytes_to_pad = block_size - len(plain_text) % block_size #python2
        ascii_string = chr(number_of_bytes_to_pad)
        padding_str = number_of_bytes_to_pad * ascii_string
        padded_plain_text = plain_text + padding_str
        return padded_plain_text.encode("utf-8")  # python3
        # return padded_plain_text #python2

    def EncodeBase64URLSafeString(self, result):
        return base64.urlsafe_b64encode(result).decode("utf-8").rstrip("=")


class GalaxyExternalApi(models.Model):
    _inherit = 'galaxy.external.api'

    request_auth = fields.Reference(selection_add=[
        ('galaxy.external.api.auth.bairong.ak', 'BaiRong AccessToken'),
    ], string='认证方式')
