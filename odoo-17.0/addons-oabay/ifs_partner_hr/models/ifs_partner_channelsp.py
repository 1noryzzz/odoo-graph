# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingPartnerChannelsp(models.Model):
    _inherit = 'ifs.partner.channelsp'

    def action_create_root_user(self):
        return {
            'name': _('创建根用户'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.channelsp.root.user',
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
            'res_model': 'ifs.partner.channelsp.legal.idcard.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
