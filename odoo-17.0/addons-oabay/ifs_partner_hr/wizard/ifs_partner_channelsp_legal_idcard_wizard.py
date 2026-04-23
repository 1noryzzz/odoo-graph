# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingChannelspLegalIdcardWizard(models.TransientModel):
    _name = 'ifs.partner.channelsp.legal.idcard.wizard'
    _inherit = 'ifs.base.company.legal.idcard.wizard'
    _description = '更新服务商法人身份证'
