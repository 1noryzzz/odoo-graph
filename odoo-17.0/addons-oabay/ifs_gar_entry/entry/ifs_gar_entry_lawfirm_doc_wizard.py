# -*- coding: utf-8 -*-

from odoo import _, api, models, fields




class GuaranteeAccountsRecEntryLawfirmDocWizard(models.TransientModel):
    _name = 'ifs.gar.entry.lawfirm.doc.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '律师事务所进件流程--附件信息'
    _ref_model = 'ifs.gar.entry.lawfirm'

    entry_id = fields.Many2one(
        'ifs.gar.entry.lawfirm', required=True, ondelete='restrict', index=True)

    reception_picture = fields.Binary('前台照')
    office_area_picture = fields.Binary('公司办公区照片')

    def action_next(self):
        self.entry_id.write({
            'reception_picture': self.reception_picture,
            'office_area_picture': self.office_area_picture,
        })

        return super().action_next()
