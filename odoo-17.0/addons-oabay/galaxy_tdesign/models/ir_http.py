# -*- coding: utf-8 -*-

from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        user = self.env.user
        session_info = super().session_info()

        if user.main_menu_style and user.main_menu_style != 'follow':
            session_info['main_menu_style'] = user.main_menu_style
        else:
            session_info['main_menu_style'] = self.env['ir.config_parameter'].sudo(
            ).get_param('galaxy_tdesign.main_menu_style')

        return session_info
