# -*- coding: utf-8 -*-

from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    area_id = fields.Many2one(
        "res.country.area", string='Area', ondelete='restrict',
        domain="[('state_id', '=?', state_id)]")
