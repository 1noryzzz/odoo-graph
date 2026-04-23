# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    global_disable_faceid = fields.Boolean(
        string="全局禁用人脸核身", config_parameter='ifs.contract.global.disable.faceid', default=False)
    face_secret_id = fields.Char(
        string="secret_id", config_parameter='ifs.contract.face.secret.id')
    face_secret_key = fields.Char(
        string="secret_key", config_parameter='ifs.contract.face.secret.key')
    face_app_id = fields.Char(
        string="appId", config_parameter='ifs.contract.face.app.id')
    face_app_secret = fields.Char(
        string="secret", config_parameter='ifs.contract.face.app.secret')
