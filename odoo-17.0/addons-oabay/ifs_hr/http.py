# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


def authenticate_env(env_request=None):
    _request = env_request or request
    if _request.params.get('otp_check', '0') != '0':
        return {
            'ot_password': _request.params.get('ot_password', '00000000')
        }
    else:
        return {}


# monkey patch
http.authenticate_env = authenticate_env
