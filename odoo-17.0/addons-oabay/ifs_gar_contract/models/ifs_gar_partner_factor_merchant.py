# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorMerchant(models.Model):
    _inherit = 'ifs.gar.partner.factor.merchant'

    f41_contract_info_id = fields.Many2one(
        'ifs.contract.info', string="征信查询授权书")
    f41_contract_name = fields.Char(
        '征信查询授权书', related='f41_contract_info_id.name', readonly=True)
    f41_contract_pdf = fields.Binary(related='f41_contract_info_id.contract')
    f41_contract_state = fields.Selection(related='f41_contract_info_id.state')

    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书托管')
    f42_contract_name = fields.Char(
        '数字证书托管', related='f42_contract_info_id.name', readonly=True)
    f42_contract_state = fields.Selection(related='f42_contract_info_id.state')
    f42_contract_pdf = fields.Binary(related='f42_contract_info_id.contract')

    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='数字证书申请')
    f43_contract_name = fields.Char(
        '数字证书申请', related='f43_contract_info_id.name', readonly=True)
    f43_contract_state = fields.Selection(related='f43_contract_info_id.state')
    f43_contract_pdf = fields.Binary(related='f43_contract_info_id.contract')
