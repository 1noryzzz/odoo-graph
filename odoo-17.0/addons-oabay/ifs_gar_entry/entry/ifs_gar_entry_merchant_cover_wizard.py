# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantCoverWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.cover.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
