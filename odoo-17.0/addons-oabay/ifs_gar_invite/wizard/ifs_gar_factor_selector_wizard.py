# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsFactorSelectorWizard(models.TransientModel):
    _name = 'ifs.gar.factor.selector.wizard'
    _description = '邀请合伙人向导'

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', required=True)
    franchisee_id = fields.Many2one('ifs.partner.franchisee', string='合伙人')
    supplier_id = fields.Many2one('ifs.partner.supplier', string='供应方')

    def choice_factor(self):
        if self.franchisee_id:
            return {
                'name': _('邀请供应方向导'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.invite.supplier.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_franchisee_id': self.franchisee_id.id,
                    'default_factor_id': self.factor_id.id,
                }
            }
        elif self.supplier_id:
            return {
                'name': _('邀请采购方向导'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.invite.merchant.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_supplier_id': self.supplier_id.id,
                    'default_factor_id': self.factor_id.id,
                }
            }
