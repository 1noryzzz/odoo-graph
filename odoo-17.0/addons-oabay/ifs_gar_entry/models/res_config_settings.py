# -*- coding: utf-8 -*-

from email.policy import default
from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    verification_legalperson_name = fields.Boolean(
        '验证法人姓名', config_parameter='ifs.gar.entry.verification.legalperson.name', default=False)
    hezongyy_secret_key = fields.Char(
        '药易购secretKey', config_parameter='ifs.gar.entry.hezongyy.secret.key', default=False)
