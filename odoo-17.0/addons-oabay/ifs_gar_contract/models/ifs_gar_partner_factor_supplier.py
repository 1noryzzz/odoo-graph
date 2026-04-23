# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerFactorSupplier(models.Model):
    _inherit = 'ifs.gar.partner.factor.supplier'

    t17_contract_info_id = fields.Many2one('ifs.contract.info', string='最高额度合同')
    t17_contract_name = fields.Char(
        '最高额度合同', related='t17_contract_info_id.name', readonly=True)
    t17_contract_state = fields.Selection(related='t17_contract_info_id.state')
    t17_contract_pdf = fields.Binary(related='t17_contract_info_id.contract')

    t21_contract_info_id = fields.Many2one('ifs.contract.info', string='保密协议')
    t21_contract_name = fields.Char(
        '保密协议', related='t21_contract_info_id.name', readonly=True)
    t21_contract_state = fields.Selection(related='t21_contract_info_id.state')
    t21_contract_pdf = fields.Binary(related='t21_contract_info_id.contract')

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
