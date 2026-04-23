# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerFactor(models.Model):
    _name = 'ifs.partner.factor'
    _description = '保理方信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'factor'

    @api.model_create_multi
    def create(self, vals_list):
        factors = super().create(vals_list)
        for factor in factors:
            factor.ifs_company_id.active_ifs_partner(factor._ifs_partner)

        return factors

    def action_create_business_license(self):
        return {
            'name': _('更新营业执照'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.factor.business.license.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }

    def action_update_account(self):
        return {
            'name': _('更新银行账户'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.factor.bank.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
