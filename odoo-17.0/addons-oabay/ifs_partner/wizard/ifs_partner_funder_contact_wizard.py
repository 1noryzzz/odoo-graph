# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import _, api, models, fields


class InclusiveFinancingFunderContactWizard(models.TransientModel):
    _name = 'ifs.partner.funder.contact.wizard'
    _inherit = 'ifs.base.company.contact.wizard'
    _description = '创建资金方向导--添加联系人'