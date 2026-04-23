# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerLawFirm(models.Model):
    _name = 'ifs.partner.lawfirm'
    _description = '律师事务所基本信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'lawfirm'
