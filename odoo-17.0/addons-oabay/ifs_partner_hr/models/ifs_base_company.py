# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingBaseCompany(models.Model):
    _name = 'ifs.base.company'
    _inherit = ['ifs.base.company']

    root_employee_id = fields.Many2one(
        'hr.employee', string='合作伙伴根用户', ondelete='restrict')
    legal_idcard_id = fields.Many2one(
        'hr.employee.idcard', related='root_employee_id.idcard_id', string='身份证信息')
    legal_id_number = fields.Char(
        '身份证号码', related='legal_idcard_id.idcard_no', store=True, tracking=True)
    legal_address = fields.Char('身份证地址', related='legal_idcard_id.address')
    legal_authority = fields.Char('签发机关', related='legal_idcard_id.authority')
    legal_idcard_expiry_date = fields.Char(
        related='root_employee_id.idcard_expiry_date', string='身份证有效期')
    legal_front_image = fields.Image(
        related='legal_idcard_id.front_image', string='身份证人像面')
    legal_back_image = fields.Image(related='legal_idcard_id.back_image', string='身份证国徽面')

    def active_ifs_partner(self, ifs_partner):
        super().active_ifs_partner(ifs_partner)
        self.env['ifs.work.position'].create_default_wp(
            self.company_id, ifs_partner)

    def inactive_ifs_partner(self, ifs_partner):
        company_id = self.company_id.id
        super().inactive_ifs_partner(ifs_partner)
        self.env['ifs.work.position'].unlink_ifs_partner_wp(
            company_id, ifs_partner)

    def action_create_legal_idcard(self):
        return {
            'name': _('更新法人身份证信息'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.base.company.legal.idcard.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.id,
            }
        }
