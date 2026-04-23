# -*- coding: utf-8 -*-

import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class InclusiveFinancingContractInformation(models.Model):
    _inherit = 'ifs.contract.info'

    partner_one = fields.Reference(selection_add=[
        ('ifs.partner.factor', '保理方'),
        ('ifs.partner.franchisee', '合伙人'),
        ('ifs.partner.funder', '资金方'),
        ('ifs.partner.merchant', '采购方'),
        ('ifs.partner.supplier', '供应方'),
        ('res.users', '个人'),
    ])
    partner_two = fields.Reference(selection_add=[
        ('ifs.partner.factor', '保理方'),
        ('ifs.partner.franchisee', '合伙人'),
        ('ifs.partner.funder', '资金方'),
        ('ifs.partner.merchant', '采购方'),
        ('ifs.partner.supplier', '供应方'),
        ('res.users', '个人'),
    ])
    partner_three = fields.Reference(selection_add=[
        ('ifs.partner.factor', '保理方'),
        ('ifs.partner.franchisee', '合伙人'),
        ('ifs.partner.funder', '资金方'),
        ('ifs.partner.merchant', '采购方'),
        ('ifs.partner.supplier', '供应方'),
    ])
    partner_four = fields.Reference(selection_add=[
        ('ifs.partner.factor', '保理方'),
        ('ifs.partner.franchisee', '合伙人'),
        ('ifs.partner.funder', '资金方'),
        ('ifs.partner.merchant', '采购方'),
        ('ifs.partner.supplier', '供应方'),
    ])
