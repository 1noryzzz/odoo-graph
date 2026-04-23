# -*- coding: utf-8 -*-
from odoo.exceptions import RedirectWarning, UserError

from odoo import _, api, models, fields


class InclusiveFinancingFunderLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.funder.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新保理方法人身份证'
