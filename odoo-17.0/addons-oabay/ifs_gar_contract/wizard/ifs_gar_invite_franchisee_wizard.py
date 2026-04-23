# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteFranchiseeWizard(models.TransientModel):
    _inherit = 'ifs.gar.invite.franchisee.wizard'
    _step_models = [
        'ifs.gar.invite.franchisee.wizard',
        'ifs.gar.invite.franchisee.contract.wizard',
        'ifs.gar.invite.franchisee.root.user.wizard',
    ]
