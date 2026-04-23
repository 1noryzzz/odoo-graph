# -*- coding: utf-8 -*-

from odoo import http, tools
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class GalaxyBase(Website):

    def get_qr_providers(self, *args, **kw):
        return []

    @http.route()
    def web_login(self, *args, **kw):
        if 'qr_providers' not in request.params:
            request.params['qr_providers'] = sorted(
                self.get_qr_providers(*args, **kw), key=lambda p: p['sequence'])
        if 'default_qr_login' not in request.params:
            request.params['default_qr_login'] = True
        if 'website_domain' not in request.params:
            request.params['website_domain'] = request.website.domain

        response = super(GalaxyBase, self).web_login(*args, **kw)
        '''
        默认不给在登录时选择数据库，而改为使用网站设置，通过域名去设默认数据库
        '''
        response.qcontext['default_db_from_domain'] = True
        return response

    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        if 'qr_providers' not in qcontext:
            qcontext['qr_providers'] = sorted(
                self.get_qr_providers(), key=lambda p: p['sequence'])
        if 'default_qr_login' not in qcontext:
            qcontext['default_qr_login'] = False
        if 'website_domain' not in qcontext:
            qcontext['website_domain'] = request.website.domain
        return qcontext
