# -*- coding: utf-8 -*-

from odoo import _, api, models, fields

class GuaranteeAccountsRecSales(models.Model):
    _inherit = 'ifs.gar.sales'

    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书托管')
    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书申请')
    p01_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='事业合伙人合作协议')
