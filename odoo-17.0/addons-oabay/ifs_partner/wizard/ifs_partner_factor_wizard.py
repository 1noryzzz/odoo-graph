# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingFactorWizard(models.TransientModel):
    _name = 'ifs.partner.factor.wizard'
    _inherit = 'ifs.base.company.wizard'
    _description = '创建保理方向导'
    _step_models = [
        'ifs.partner.factor.wizard',
        'ifs.partner.factor.business.license.wizard',
        'ifs.partner.factor.bank.wizard',
    ]

    def action_confirm(self):
        ifs_base_company = super().action_confirm()
        factor = self.env['ifs.partner.factor'].search(
            [('company_registry', '=', ifs_base_company.company_registry)])
        if not factor.exists():
            if ifs_base_company.ifs_partners and factor._ifs_partner in ifs_base_company.ifs_partners:
                # 这种情况是数据异常，不应该出现
                raise UserError('当前公司已以保理方的身份存在，请勿重复创建！')
            else:
                factor = self.env['ifs.partner.factor'].create({
                    'ifs_company_id': ifs_base_company.id
                })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _(f'已成功创建保理方{factor.name}，请继续完善保理方信息'),
                    'next': {
                        'name': _('保理方'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.partner.factor',
                        'res_id': factor.id,
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
                                    'next_model': self._next_model(self._next_model(self._name)),
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
                    'message': _(f'保理方{factor.name}已存在！'),
                    'next': {
                        'name': _('保理方'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.partner.factor',
                        'res_id': factor.id,
                        'target': 'current'
                    }
                }
            }
