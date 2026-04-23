# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplierCoverWizard(models.TransientModel):
    _name = 'ifs.gar.entry.supplier.cover.wizard'
    _inherit = ['ifs.gar.entry.step']
    # _inherits = {'ifs.gar.entry.supplier': 'entry_id'}
    _description = '供应方进件流程--确认基本信息'
    _ref_model = 'ifs.gar.entry.supplier'

    entry_id = fields.Many2one(
        'ifs.gar.entry.supplier', required=True, ondelete='restrict', index=True)

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)
