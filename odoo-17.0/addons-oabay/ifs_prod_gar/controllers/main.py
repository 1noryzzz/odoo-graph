# -*- coding: utf-8 -*-

from urllib.parse import urlparse

from odoo import _, http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class GuaranteeAccountsRecProduct(Website):

    @http.route()
    def web_login(self, redirect=None, **kw):
        is_mobile = kw.get('is_mobile', False)
        redirect_url = urlparse(redirect)
        if redirect_url.query and 'is_mobile=' in redirect_url.query:
            is_mobile = True

        response = super(
            GuaranteeAccountsRecProduct, self).web_login(redirect, **kw)

        if is_mobile and not request.params['login_success']:
            response = request.render(
                'ifs_prod_gar.mobile_login', response.qcontext)

        return response
