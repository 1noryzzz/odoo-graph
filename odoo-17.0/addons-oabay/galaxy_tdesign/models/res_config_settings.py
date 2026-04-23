# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    main_menu_style = fields.Selection([
        ('foldadd', '全部折叠'),
        ('expandonce', '单个展开'),
        ('expandall', '全部展开')], string="左侧菜单设置",
        required=True, default='foldadd',
        config_parameter='galaxy_tdesign.main_menu_style')
