# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntrySupplierBInfoWizard(models.TransientModel):
    _inherit = 'ifs.gar.entry.supplier.base.info.wizard'
    _ref_model = 'ifs.gar.entry.supplier'

    def action_next(self):
        if self.entry_id.invite_id.ifs_company_id.org_auth_state != 'certified':
            self.entry_id.invite_id.ifs_company_id.sudo().certificate_company()

        return super().action_next()
