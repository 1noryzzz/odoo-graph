# -*- coding: utf-8 -*-


from odoo import _, models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    ifs_partners = fields.Json('业务角色集合', default=[])
