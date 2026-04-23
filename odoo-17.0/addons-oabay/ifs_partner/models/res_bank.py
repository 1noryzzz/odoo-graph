# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class InclusiveFinancingBaseBank(models.Model):
    _inherit = 'res.bank'
    
    dock_method = fields.Selection([
        ('ums_dock', '银企直接'),
        ('lading_bill', '提单接口'),
        ('not_dock', '未对接'),
    ], string='对接方式')