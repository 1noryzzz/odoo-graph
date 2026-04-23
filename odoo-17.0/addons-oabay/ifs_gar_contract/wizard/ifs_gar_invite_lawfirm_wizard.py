# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteLawfirmWizard(models.TransientModel):
    _inherit = 'ifs.gar.invite.lawfirm.wizard'
    _step_models = [
        'ifs.gar.invite.lawfirm.wizard',
        'ifs.gar.invite.lawfirm.contract.wizard',
        'ifs.gar.invite.lawfirm.root.user.wizard',
    ]
