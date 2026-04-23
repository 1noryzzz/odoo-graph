# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorFranchisee(models.Model):
    _inherit = 'ifs.gar.partner.factor.franchisee'

    p01_contract_info_id = fields.Many2one('ifs.contract.info', string='事业合伙人合作协议')
    p01_contract_name = fields.Char(
        '事业合伙人合作协议', related='p01_contract_info_id.name', readonly=True)
    p01_contract_state = fields.Selection(related='p01_contract_info_id.state')
    p01_contract_pdf = fields.Binary(related='p01_contract_info_id.contract')

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
