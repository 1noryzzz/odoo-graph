# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteSupplier(models.Model):
    _inherit = 'ifs.gar.invite.supplier'

    cut_off_time = fields.Float('日切时间', default=4.5)
    fee_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution.ver', string='收费方案')

    def choice_fee_solution(self):
        self.ensure_one()

        return {
            'name': _('选择收费方案'),
            'type': 'ir.actions.act_window',
            'res_model': 'ifs.gar.invite.supplier.fee.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
        
    def start_entry(self):
        res = super().start_entry()
        waiting_list = self.filtered(lambda r: r.state != 'ready')
        if len(waiting_list) == 1 and waiting_list.state in ['draft', 'sended'] and not waiting_list.fee_solution_id:
            raise AccessDenied(_('当前供应方还未设置收费方案，请先进行设置！'))
        return res