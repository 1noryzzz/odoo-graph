# -*- coding: utf-8 -*-

from odoo.exceptions import UserError

from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteMerchantWizard(models.TransientModel):
    _name = 'ifs.gar.invite.merchant.wizard'
    _inherit = 'ifs.base.company.wizard'
    _description = '邀请采购方向导'
    _step_models = [
        'ifs.gar.invite.merchant.wizard',
        'ifs.gar.invite.merchant.root.user.wizard',
    ]
    
    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True, string='保理方', index=True, ondelete='restrict')
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', ondelete='restrict')
    
    def action_confirm(self):
        ifs_base_company = super().action_confirm()
        invite_merchant = self.env['ifs.gar.invite.merchant'].search([
            ('company_registry', '=', ifs_base_company.company_registry),
            ('supplier_id', '=', self.supplier_id.id)
        ])
        if not invite_merchant.exists():
            invite_merchant = self.env['ifs.gar.invite.merchant'].create({
                'ifs_company_id': ifs_base_company.id,
                'factor_id': self.factor_id.id,
                'supplier_id': self.supplier_id.id,
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _(f'已创建对采购方{invite_merchant.name}，请继续完善信息并发出邀请！'),
                    'next': {
                        'name': _('采购方邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.merchant',
                        'res_id': invite_merchant.id,
                        'target': 'current',
                        'context': {
                            'open_wizard': True,
                            'wizard_action': {
                                'name': self.env[self._next_model(self._name)]._description,
                                'type': 'ir.actions.act_window',
                                'view_mode': 'form',
                                'views': [[False, 'form']],
                                'res_model': self._next_model(self._name),
                                'res_id': False,
                                'target': 'new',
                                'context': {
                                    'default_ifs_company_id': ifs_base_company.id,
                                    'prev_model': self._name,
                                    'next_model': self._next_model(self._next_model(self._name))
                                }
                            }
                        }
                    }
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _(f'采购方{invite_merchant.name}已被邀请！'),
                    'next': {
                        'name': _('采购方邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.merchant',
                        'res_id': invite_merchant.id,
                        'target': 'current'
                    }
                }
            }