# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantRjWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.rejected.info.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--审批拒绝'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    reject_reason = fields.Html('驳回原因', related='entry_id.reject_reason')
