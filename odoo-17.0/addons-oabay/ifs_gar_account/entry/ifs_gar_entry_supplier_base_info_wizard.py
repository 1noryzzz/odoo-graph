# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecEntrySupplierBInfoWizard(models.TransientModel):
    _inherit = 'ifs.gar.entry.supplier.base.info.wizard'

    currency_id = fields.Many2one(
        'res.currency', related="entry_id.currency_id", string="Currency")
    total_quota = fields.Monetary('合作额度', required=True, default=10000000.00)

    def action_next(self):
        self.entry_id.write({
            'total_quota': self.total_quota,
        })

        return super().action_next()
