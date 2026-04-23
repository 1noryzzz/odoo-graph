# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingFunderBankWizard(models.TransientModel):
    _name = 'ifs.partner.funder.bank.wizard'
    _inherit = 'ifs.base.company.bank.wizard'
    _description = '创建资金方向导--银行账户'

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

        funder = self.env['ifs.partner.funder'].search(
            [('ifs_company_id', '=', self.ifs_company_id.id)])
        if not funder.exists():
            raise UserError('当前公司不是资金方，无法创建资金方开户许可证！')

        funder.write({
            'deposit_license': self.deposit_license,
        })
