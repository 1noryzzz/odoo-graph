# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingFunderWizard(models.TransientModel):
    _name = 'ifs.partner.funder.wizard'
    _inherit = 'ifs.base.company.wizard'
    _description = '创建资金方向导'
    _step_models = [
        'ifs.partner.funder.wizard',
        'ifs.partner.funder.business.license.wizard',
        # 'ifs.partner.funder.bank.wizard',
    ]
    
    type = fields.Selection([('bank', '银行'), ('microfinance', '小贷'),
                            ('private', '私募'), ('vc', '风险投资')], required=True, string="资金方类型")

    def action_confirm(self):
        factor = self.env['ifs.partner.factor'].search(
            [('company_id', '=', self.env.company.id)])
        if not factor:
            raise UserError("只有保理方才能创建订单")
        ifs_base_company = super().action_confirm()
        funder = self.env['ifs.partner.funder'].search(
            [('company_registry', '=', ifs_base_company.company_registry)])
        if not funder.exists():
            if ifs_base_company.ifs_partners and funder._ifs_partner in ifs_base_company.ifs_partners:
                # 这种情况是数据异常，不应该出现
                raise UserError('当前公司已以资金方的身份存在，请勿重复创建！')
            else:
                funder = self.env['ifs.partner.funder'].create({
                    'ifs_company_id': ifs_base_company.id,
                    'type':self.type,
                })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _(f'已成功创建资金方{funder.name}，请继续完善资金方信息'),
                    'next': {
                        'name': _('资金方'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.partner.funder',
                        'res_id': funder.id,
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
                    'message': _(f'资金方{funder.name}已存在！'),
                    'next': {
                        'name': _('资金方'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'views': [[False, 'form']],
                        'res_model': 'ifs.partner.funder',
                        'res_id': funder.id,
                        'target': 'current'
                    }
                }
            }
