# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    enable_ipinfo_io = fields.Boolean(
        "启用IPinfo.io", config_parameter="galaxy.qq.api.enable.ipinfo"
    )
