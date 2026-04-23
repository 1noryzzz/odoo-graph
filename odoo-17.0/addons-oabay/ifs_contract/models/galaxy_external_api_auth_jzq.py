# -*- coding: utf-8 -*-

import hashlib
import string
import time
import random
import requests
import ssl
from urllib3 import poolmanager
from requests.adapters import HTTPAdapter
from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GalaxyExternalApiAuthAceessToken(models.Model):
    _name = 'galaxy.external.api.auth.jzq'
    _inherit = ['galaxy.external.api.auth']
    _description = '君子签AccesToken'
    
    def do_auth(self, headers=None, query=None, body=None,rargs=None):
        super().do_auth(headers, query, body,rargs)
        (app_key, app_secret) = self._get_param_config()
        
        nonce = ''.join(random.sample(
            string.ascii_letters + string.digits, 32))
        ts = int(time.time())

        sign_str = ''.join([
            'nonce', nonce, 'ts', str(ts),
            'app_key', app_key, 'app_secret', app_secret
        ])
        sign = hashlib.sha1(sign_str.encode('utf-8')).hexdigest()
        
        body.update({
            'nonce':nonce
        })
        query.update({
            'app_key':app_key,
            'ts':ts,
            'sign':sign,
            'encry_method':'sha1'
        })

        
        
    def _get_param_config(self):
        cfg = self.env['ir.config_parameter'].sudo()
        test_env = cfg.get_param('ifs.contract.sign.jzq.test.env', False)
        if test_env:
            appKey = cfg.get_param('ifs.contract.sign.jzq.app.key.test', False)
            appSecret = cfg.get_param(
                'ifs.contract.sign.jzq.app.secret.test', False)
        else:
            appKey = cfg.get_param('ifs.contract.sign.jzq.app.key', False)
            appSecret = cfg.get_param(
                'ifs.contract.sign.jzq.app.secret', False)
        return (appKey, appSecret)
        
        
        
class GalaxyExternalApiGuoRenPcic(models.Model):
    _name = 'galaxy.external.api.auth.guorenpcic'
    _inherit = ['galaxy.external.api.auth']
    _description = '国任保险认证'
    
    def do_auth(self, headers=None, query=None, body=None,rargs=None):
        super().do_auth(headers, query, body,rargs)
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        adapter = HTTPAdapter()
        adapter.poolmanager = poolmanager.PoolManager(
                    ssl_version=ssl.PROTOCOL_TLS,
                    ssl_context=ctx)
        session = requests.session()
        session.mount('https://',adapter)
        return session

class GalaxyExternalApiDisableWarnings(models.Model):
    _name = 'galaxy.external.api.disable.warnings'
    _inherit = ['galaxy.external.api.auth']
    _description = '忽略证书验证警告'
    
    def do_auth(self, headers=None, query=None, body=None,rargs=None):
        super().do_auth(headers, query, body,rargs)
        requests.packages.urllib3.disable_warnings()
        serrion = requests.session()
        return serrion
        
        
        
class GalaxyExternalApi(models.Model):
    _inherit = 'galaxy.external.api'

    request_auth = fields.Reference(selection_add=[
        ('galaxy.external.api.auth.jzq', 'jzq AccessToken'),
        ('galaxy.external.api.auth.guorenpcic', '国任保险认证'),
        ('galaxy.external.api.disable.warnings', '忽略证书验证警告'),
    ], string='认证方式')