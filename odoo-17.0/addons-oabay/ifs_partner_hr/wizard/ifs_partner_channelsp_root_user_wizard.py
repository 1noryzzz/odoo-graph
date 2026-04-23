# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingChannelspRootUserWizard(models.TransientModel):
    _name = 'ifs.partner.channelsp.root.user'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建服务商根用户'
