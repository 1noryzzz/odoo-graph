# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError, RedirectWarning


class InclusiveFinancingFunderBusinessLicenseWizard(models.TransientModel):
    _name = 'ifs.partner.funder.business.license.wizard'
    _inherit = 'ifs.base.company.business.license.wizard'
    _description = '创建资金方向导--营业执照'
    _step_models = [
        'ifs.partner.funder.wizard',
        'ifs.partner.funder.business.license.wizard',
        'ifs.partner.funder.bank.wizard',
    ]

    @api.depends('ifs_company_id')
    def _compute_current_step(self):
        super()._compute_current_step()
        for record in self:
            if record.ifs_company_id:
                record.update({
                    'current_step': 3,
                })

    @api.onchange('business_license')
    def business_license_check(self):
        try:
            return super().business_license_check()
        except Exception as e:
            raise RedirectWarning(
                message=e.name,
                button_text=_("重新上传"),
                action={
                    'name': self._description,
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'context': {
                        'default_ifs_company_id': self.ifs_company_id.id,
                        'prev_model': self._context.get('prev_model'),
                        'next_model': self._context.get('next_model'),
                    }
                },
            )

    def action_confirm(self):
        # 这里覆盖掉 ifs.base.company.business.license.wizard 的 action_confirm 方法，
        # 主要是因为直接在上一层级更新，不会更新当前表的最后修改时间，导致图片缓存无法更新
        funder = self.env['ifs.partner.funder'].search(
            [('ifs_company_id', '=', self.ifs_company_id.id)])
        if not funder.exists():
            raise UserError('当前公司不是资金方，无法创建资金方营业执照！')

        funder.write({
            'business_license': self.business_license,
        })

        if self.is_in_step and self._context.get('next_model', False):
            return {
                'name': self.env[self._context.get('next_model')]._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': self._context.get('next_model'),
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                    'prev_model': self._name,
                    'next_model': self._next_model(self._context.get('next_model')),
                }
            }

    def nosave_pass(self):
        return {
            'name': self.env[self._context.get('next_model')]._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._context.get('next_model'),
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.env.context.get('default_ifs_company_id'),
                'prev_model': self._name,
                'next_model': self._next_model(self._context.get('next_model')),
            }
        }
