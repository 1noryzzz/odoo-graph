# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecInviteSupplierFeeWizard(models.TransientModel):
    _name = 'ifs.gar.invite.supplier.fee.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '邀请供应方向导--收费方式设置'
    _step_models = [
        'ifs.gar.invite.supplier.wizard',
        'ifs.gar.invite.supplier.fee.wizard',
        'ifs.gar.invite.supplier.root.user.wizard',
    ]

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'ifs_company_id' in fields and res.get('ifs_company_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                invite_supplier = self.env['ifs.gar.invite.supplier'].search([
                    ('ifs_company_id', '=', res.get('ifs_company_id')),
                    ('factor_id.company_id', '=', self.env.company.id)
                ], limit=1)
                if invite_supplier.id:
                    res.setdefault(
                        'fee_solution_id',
                        invite_supplier.fee_solution_id.id)
                    res.setdefault('cut_off_time', invite_supplier.cut_off_time)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可设置收费方案！'))
        return res

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
    cut_off_time = fields.Float('日切时间', default=4.5)
    fee_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution.ver', string='收费方案')
    description = fields.Text(
        string='收费方案描述', related='fee_solution_id.description')
    contract_content = fields.Html(
        string='收费方案合同内容', related='fee_solution_id.contract_content')

    @api.depends('ifs_company_id')
    def _compute_current_step(self):
        super()._compute_current_step()
        for record in self:
            if record.ifs_company_id:
                record.update({
                    'current_step': 3,
                })

    def action_confirm(self):
        invite_supplier = self.env['ifs.gar.invite.supplier'].search(
            [('ifs_company_id', '=', self.ifs_company_id.id), ('factor_id.company_id', '=', self.env.company.id)])
        if invite_supplier:
            invite_supplier.update({
                'cut_off_time': self.cut_off_time,
                'fee_solution_id': self.fee_solution_id.id
            })

        if self.is_in_step and self._context.get('next_model', False):
            return {
                'name': self.env[self._next_model(self._name)]._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': self._next_model(self._name),
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                    'prev_model': self._name,
                    'next_model': self._next_model(self._next_model(self._name)),
                }
            }
