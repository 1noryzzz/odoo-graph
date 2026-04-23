# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingPartnerInsurant(models.Model):
    _inherit = 'ifs.partner.insurant'

    def action_create_root_user(self):
        return {
            'name': _('创建根用户'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.insurant.root.user.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }

    def action_create_legal_idcard(self):
        return {
            'name': _('更新法人身份证信息'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.insurant.legal.idcard.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
