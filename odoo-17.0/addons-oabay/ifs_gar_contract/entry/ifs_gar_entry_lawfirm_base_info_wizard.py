# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryLawfirmBInfoWizard(models.TransientModel):
    _inherit = 'ifs.gar.entry.lawfirm.base.info.wizard'
    _ref_model = 'ifs.gar.entry.lawfirm'

    def action_next(self):
        if self.entry_id.invite_id.ifs_company_id.org_auth_state != 'certified':
            self.entry_id.invite_id.ifs_company_id.sudo().certificate_company()

        return super().action_next()
