# -*- coding: utf-8 -*-


from odoo import _, api, fields, models


class InclusiveFinanchingHrEmployee(models.Model):
    _inherit = ['hr.employee']

    is_root = fields.Boolean('是否为公司根账户', default=False)
