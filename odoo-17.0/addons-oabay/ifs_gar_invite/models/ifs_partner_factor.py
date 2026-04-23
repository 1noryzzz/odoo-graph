# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerFactor(models.Model):
    _inherit = 'ifs.partner.factor'

    invite_supplier_ids = fields.One2many(
        'ifs.gar.invite.supplier', 'factor_id', string='邀请供应方记录', copy=False)
    invite_franchisee_ids = fields.One2many(
        'ifs.gar.invite.franchisee', 'factor_id', string='邀请合伙人记录', copy=False)
    invite_lawfirm_ids = fields.One2many(
        'ifs.gar.invite.lawfirm', 'factor_id', string='邀请律师事务所记录', copy=False)
