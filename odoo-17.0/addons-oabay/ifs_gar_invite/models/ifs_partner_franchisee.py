# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerFranchisee(models.Model):
    _inherit = 'ifs.partner.franchisee'

    invite_supplier_ids = fields.One2many(
        'ifs.gar.invite.supplier', 'franchisee_id', string='邀请供应方记录', copy=False)