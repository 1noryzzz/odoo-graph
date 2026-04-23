# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteSupplierWizard(models.TransientModel):
    _inherit = 'ifs.gar.invite.supplier.wizard'
    _step_models = [
        'ifs.gar.invite.supplier.wizard',
        'ifs.gar.invite.supplier.fee.wizard',
        'ifs.gar.invite.supplier.contract.wizard',
        'ifs.gar.invite.supplier.root.user.wizard',
    ]
