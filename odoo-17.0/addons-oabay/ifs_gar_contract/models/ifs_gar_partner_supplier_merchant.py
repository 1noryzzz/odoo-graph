# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingGarPartnerSupplierMerchant(models.Model):
    _inherit = 'ifs.gar.partner.supplier.merchant'

    t18_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='最高子额度合同')
    t18_contract_name = fields.Char(
        '最高子额度合同', related='t18_contract_info_id.name', readonly=True)
    t18_contract_state = fields.Selection(related='t18_contract_info_id.state')
    t18_contract_pdf = fields.Binary(related='t18_contract_info_id.contract')

    t18a_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='告知确认函')
    t18a_contract_name = fields.Char(
        '告知确认函', related='t18a_contract_info_id.name', readonly=True)
    t18a_contract_state = fields.Selection(related='t18a_contract_info_id.state')
    t18a_contract_pdf = fields.Binary(related='t18a_contract_info_id.contract')
    
    t22_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='最高额不可撤销担保书')
    t22_contract_name = fields.Char(
        '最高额不可撤销担保书', related='t22_contract_info_id.name', readonly=True)
    t22_contract_state = fields.Selection(related='t22_contract_info_id.state')
    t22_contract_pdf = fields.Binary(related='t22_contract_info_id.contract')
