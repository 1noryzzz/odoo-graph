# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantBtwWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.btw.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--退回补充资料'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    btw_reason = fields.Html('驳回原因', related='entry_id.btw_reason')

    def action_next(self):
        return self.env[self._ref_model].create({
            'ifs_company_id': self.entry_id.ifs_company_id.id,
            'invite_id': self.entry_id.invite_id.id,
            'last_entry_id': self.entry_id.id,
            'phone': self.entry_id.invite_id.phone,
            'email': self.entry_id.invite_id.email,
            'business_address': self.entry_id.invite_id.business_address,
        }).start_step()
