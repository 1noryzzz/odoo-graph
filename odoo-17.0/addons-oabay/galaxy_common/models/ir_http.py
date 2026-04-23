# -*- coding: utf-8 -*-

import werkzeug

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_exception_code_values(cls, exception):
        code, values = super(Http, cls)._get_exception_code_values(exception)
        if isinstance(exception, werkzeug.exceptions.BadRequest) and \
                exception.description == "Session expired (invalid CSRF token)":
            code = '400'
            values['path'] = request.httprequest.path
            values['error_message'] = "页面已超时，请点击下面按钮重新登录！"
        return (code, values)
