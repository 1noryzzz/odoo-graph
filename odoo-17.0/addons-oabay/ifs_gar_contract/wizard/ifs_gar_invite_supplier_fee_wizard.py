# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecInviteSupplierFeeWizard(models.TransientModel):
    _inherit = 'ifs.gar.invite.supplier.fee.wizard'
    _step_models = [
        'ifs.gar.invite.supplier.wizard',
        'ifs.gar.invite.supplier.fee.wizard',
        'ifs.gar.invite.supplier.contract.wizard',
        'ifs.gar.invite.supplier.root.user.wizard',
    ]
