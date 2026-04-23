# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteLawFirm(models.Model):
    _name = 'ifs.gar.invite.lawfirm'
    _inherit = ['ifs.gar.invite.mixin']
    _description = '邀请律师事务所进件'
    _order = 'create_date desc'
    _invite_ifs_partner = 'lawfirm'
    
    _sql_constraints = [
        ('factor_lawfirm_no_uniq', 'unique (factor_id, ifs_company_id)', '此律师事务所已经邀请过了！')
    ]

    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True,
        string='保理方', index=True, ondelete='restrict', copy=False)

    state = fields.Selection([
        ('draft', '草稿'),
        ('sended', '已发邀请'),
        ('waiting', '待提交'),
        ('activation', '待开通'),
        ('ready', '已开通')
    ], string='状态', default='draft')
    
    can_send = fields.Boolean('可重发邀请信', compute="_compute_can_send")
    
    @api.depends('state')
    def _compute_can_send(self):
        for record in self:
            record.can_send = (
                record.factor_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended'])

    def start_invite(self):
        if 'factor' in (self.env.company.ifs_partners or []):
            factor = self.env['ifs.partner.factor'].search([
                ('company_id', '=', self.env.company.id)
            ])
            if not factor.exists():
                raise AccessDenied(_('当前保理方数据异常，请联系管理员！'))
            return {
                'name': _('邀请律师事务所向导'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.invite.lawfirm.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_factor_id': factor.id,
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
                'res_model': 'ifs.gar.invite.lawfirm.root.user.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                }
            }