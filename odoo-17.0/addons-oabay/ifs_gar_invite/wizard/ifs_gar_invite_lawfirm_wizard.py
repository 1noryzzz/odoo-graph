# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteLawfirmWizard(models.TransientModel):
    _name = 'ifs.gar.invite.lawfirm.wizard'
    _inherit = 'ifs.base.company.wizard'
    _description = '邀请律师事务所向导'
    _step_models = [
        'ifs.gar.invite.lawfirm.wizard',
        'ifs.gar.invite.lawfirm.root.user.wizard',
    ]

    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True, string='保理方', index=True, ondelete='restrict')

    def action_confirm(self):
        ifs_base_company = super().action_confirm()
        invite_lawfirm = self.env['ifs.gar.invite.lawfirm'].search([
            ('company_registry', '=', ifs_base_company.company_registry),
            ('factor_id', '=', self.factor_id.id)
        ])
        if not invite_lawfirm.exists():
            invite_lawfirm = self.env['ifs.gar.invite.lawfirm'].create({
                'ifs_company_id': ifs_base_company.id,
                'factor_id': self.factor_id.id
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _(f'已创建对律所{invite_lawfirm.name} 的邀约，请继续完善信息并发出邀请！'),
                    'next': {
                        'name': _('律师事务所邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.lawfirm',
                        'res_id': invite_lawfirm.id,
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
                    'message': _(f'律所{invite_lawfirm.name}已被邀请！'),
                    'next': {
                        'name': _('律师事务所邀约'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.gar.invite.lawfirm',
                        'res_id': invite_lawfirm.id,
                        'target': 'current'
                    }
                }
            }
