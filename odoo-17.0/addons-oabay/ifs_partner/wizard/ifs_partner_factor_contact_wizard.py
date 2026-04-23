# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import _, api, models, fields


class InclusiveFinancingFactorContactWizard(models.TransientModel):
    _name = 'ifs.partner.factor.contact.wizard'
    _inherit = 'ifs.base.company.contact.wizard'
    _description = '创建保理方向导--添加联系人'