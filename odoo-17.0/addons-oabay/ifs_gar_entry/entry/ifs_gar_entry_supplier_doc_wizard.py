# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplierDocWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.doc.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '供应方进件流程--附件信息'
    _ref_model = 'ifs.gar.entry.supplier'

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', required=True, ondelete='restrict', index=True)

    reception_picture = fields.Binary('前台照')
    office_area_picture = fields.Binary('公司办公区照片')

    def action_next(self):
        self.entry_id.write({
            'reception_picture': self.reception_picture,
            'office_area_picture': self.office_area_picture,
        })

        return super().action_next()
