# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerFranchisee(models.Model):
    _name = 'ifs.partner.franchisee'
    _description = '合伙人基本信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'franchisee'
