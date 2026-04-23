# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecInviteMerchant(models.Model):
    _inherit = 'ifs.gar.invite.merchant'

    approval_date = fields.Datetime('获批时间', copy=False)

    def write(self, vals):
        if 'state' in vals and vals.get('state') == 'ready' and not self.approval_date:
            vals['approval_date'] = fields.Datetime.now()
        return super().write(vals)
