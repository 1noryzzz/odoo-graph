# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingFactorBankWizard(models.TransientModel):
    _name = 'ifs.partner.factor.bank.wizard'
    _inherit = 'ifs.base.company.bank.wizard'
    _description = '创建保理方向导--银行账户'

    @api.depends('ifs_company_id')
    def _compute_current_step(self):
        super()._compute_current_step()
        for record in self:
            if record.ifs_company_id:
                record.update({
                    'current_step': 4,
                })

    def action_confirm(self):
        super().action_confirm()

        factor = self.env['ifs.partner.factor'].search(
            [('ifs_company_id', '=', self.ifs_company_id.id)])
        if not factor.exists():
            raise UserError('当前公司不是保理方，无法创建保理方开户许可证！')

        factor.write({
            'deposit_license': self.deposit_license,
        })
