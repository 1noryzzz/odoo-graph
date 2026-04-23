# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryLawfirmCoverWizard(models.TransientModel):
    _name = 'ifs.gar.entry.lawfirm.cover.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '律师事务所进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.lawfirm'

    entry_id = fields.Many2one(
        'ifs.gar.entry.lawfirm', required=True, ondelete='restrict', index=True)
