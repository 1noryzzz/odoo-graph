# -*- coding: utf-8 -*-

from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'
    
    main_menu_style = fields.Selection([
        ('follow', '跟随系统设置'),
        ('foldadd', '全部折叠'),
        ('expandonce', '单个展开'),
        ('expandall', '全部展开')], string="左侧菜单展开设置",
        default='follow')