# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta


class GuaranteeAccountsRecEntryMerchantFinishWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.finish.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--进件完成信息'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    committed = fields.Boolean('是否提交', default=False)

    def action_next(self):
        self.committed = True
        ifs_risk_credits_id = False
        if self.entry_id.legal_info:
            ifs_risk_credits_id = self.env['ifs.risk.manage.credits'].create({
                'ifs_company_id': self.entry_id.ifs_company_id.id,
                'idcard': self.entry_id.legal_id_number,
                'mobile': self.entry_id.legal_info.get('phone'),
                'name': self.entry_id.legal_name,
            }).id
        guarantor_ifs_risk_credits_id = False
        if not self.entry_id.is_self_guarantee and self.entry_id.guarantor_info:
            guarantor_ifs_risk_credits_id = self.env['ifs.risk.manage.credits'].create({
                'ifs_company_id': self.entry_id.ifs_company_id.id,
                'idcard': self.entry_id.guarantor_idcard_no,
                'mobile': self.entry_id.guarantor_info.get('guarantor_phone'),
                'name': self.entry_id.guarantor_name,
            }).id

        self.entry_id.sudo().write({
            'state': 'committed',
            'need_fetch': True,
            'ifs_risk_credits_id': ifs_risk_credits_id,
            'guarantor_ifs_risk_credits_id': guarantor_ifs_risk_credits_id,
        })
        self.env['ir.cron.trigger'].sudo().create({
            'cron_id': self.env.ref(
                'ifs_risk_manage.ir_cron_fetch_risk_manage_br_credits_info').id,
            'call_at': datetime.now() + relativedelta(seconds=5)
        })
        self.env['ir.cron.trigger'].sudo().create({
            'cron_id': self.env.ref(
                'ifs_risk_manage.ir_cron_fetch_company_info').id,
            'call_at': datetime.now() + relativedelta(seconds=15)
        })

        return super().action_next()
