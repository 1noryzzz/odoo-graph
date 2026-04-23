# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplierRjWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.reject.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '供应方进件流程--退回补充资料'
    _ref_model = 'ifs.gar.entry.supplier'

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', required=True, ondelete='restrict', index=True)
    reject_reason = fields.Html('驳回原因', related='entry_id.reject_reason')

    def action_next(self):
        return self.env['ifs.gar.entry.supplier'].create({
            'ifs_company_id': self.entry_id.ifs_company_id.id,
            'invite_id': self.entry_id.invite_id.id,
            'last_entry_id': self.entry_id.id,
            'phone': self.entry_id.invite_id.phone,
            'email': self.entry_id.invite_id.email,
            'business_address': self.entry_id.invite_id.business_address,
        }).start_step()
