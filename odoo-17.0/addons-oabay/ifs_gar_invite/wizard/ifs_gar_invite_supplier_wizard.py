# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteSupplierWizard(models.TransientModel):
    _name = 'ifs.gar.invite.supplier.wizard'
    _inherit = 'ifs.base.company.wizard'
    _description = '邀请供应方向导'
    _step_models = [
        'ifs.gar.invite.supplier.wizard',
        'ifs.gar.invite.supplier.root.user.wizard',
    ]

    franchisee_id = fields.Many2one(
        'ifs.partner.franchisee', string='合伙人', ondelete='restrict')
    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True, string='保理方', index=True, ondelete='restrict')

    def action_confirm(self):
        ifs_base_company = super().action_confirm()
        invite_supplier = self.env['ifs.gar.invite.supplier'].search([
            ('company_registry', '=', ifs_base_company.company_registry),
            ('factor_id', '=', self.factor_id.id),
        ])
        if not invite_supplier.exists():
            invite_supplier = self.env['ifs.gar.invite.supplier'].create({
                'ifs_company_id': ifs_base_company.id,
                'factor_id': self.factor_id.id,
                'franchisee_id': self.franchisee_id.id,
            })
            has_permission = self.env.user.has_group('ifs_partner.group_ifs_partner_factor_manager')

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _(f'已创建对供应方{invite_supplier.name} 的邀约，请继续完善信息并发出邀请！'),
                    'next': {
                        'name': _('供应方邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.supplier',
                        'res_id': invite_supplier.id,
                        'target': 'current',
                        'context': {
                            'open_wizard': True if not self.franchisee_id and has_permission else False,
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
                    'message': _(f'供应方{invite_supplier.name} 已被邀请！'),
                    'next': {
                        'name': _('供应方邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.supplier',
                        'res_id': invite_supplier.id,
                        'target': 'current'
                    }
                }
            }
