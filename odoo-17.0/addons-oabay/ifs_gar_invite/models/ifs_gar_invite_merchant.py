# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteMerchant(models.Model):
    _name = 'ifs.gar.invite.merchant'
    _description = '邀请采购方进件'
    _inherit = ['ifs.gar.invite.mixin']
    _order = 'create_date desc'
    _invite_ifs_partner = 'merchant'

    _sql_constraints = [
        ('supplier_merchant_no_uniq',
         'unique (supplier_id, ifs_company_id)', '此采购方已经邀请过了！')
    ]

    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True,
        string='保理方', index=True, ondelete='restrict', copy=False)
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', required=True, string='供应方', index=True, ondelete='restrict', copy=False)
    state = fields.Selection([
        ('draft', '草稿'),
        ('sended', '已发邀请'),
        ('waiting', '待提交'),
        ('auditing', '待审批'),
        ('rejected', '已拒绝'),
        ('tobesign', '待签约'),
        ('ready', '已开通'),
    ], string='状态', default='draft')
    
    can_send = fields.Boolean('可重发邀请信', compute="_compute_can_send")
    
    @api.depends('state')
    def _compute_can_send(self):
        for record in self:
            record.can_send = (
                record.supplier_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended'])

    def start_invite(self):
        if 'supplier' in (self.env.company.ifs_partners or []):
            supplier = self.env['ifs.partner.supplier'].search([
                ('company_id', '=', self.env.company.id)
            ])
            if not supplier.exists() or len(supplier.factor_ids or []) == 0:
                raise AccessDenied(_('当前供应方无合作的保理方！'))
            elif len(supplier.factor_ids) > 1:
                return {
                    'name': _('选择保理方'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'ifs.gar.factor.selector.wizard',
                    'res_id': False,
                    'target': 'new',
                    'context': {
                        'default_supplier_id': supplier.id,
                    }
                }
            else:
                return {
                    'name': _('邀请采购方向导'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'ifs.gar.invite.merchant.wizard',
                    'res_id': False,
                    'target': 'new',
                    'context': {
                        'default_supplier_id': supplier.id,
                        'default_factor_id': supplier.factor_ids[0].factor_id.id,
                    }
                }
        else:
            raise AccessDenied(_('请切换到可发送邀请的公司'))

    def action_reinvite(self):
        if self.can_send:
            return {
                'name': _('添加联系人信息'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[False, 'form']],
                'res_model': 'ifs.gar.invite.merchant.root.user.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                }
            }
