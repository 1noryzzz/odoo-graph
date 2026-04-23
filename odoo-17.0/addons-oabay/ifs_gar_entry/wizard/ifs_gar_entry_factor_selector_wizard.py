# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsEntryFactorSelectorWizard(models.TransientModel):
    _name = 'ifs.gar.entry.factor.selector.wizard'
    _description = '供应方进件向导'

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', required=True, domain=lambda self: self._factor_domain())

    def _factor_domain(self):
        model_name = ''
        if self._context.get('invite_ifs_partner'):
            model_name = 'ifs.gar.invite.' + self._context.get('invite_ifs_partner')
        invite_ids = self.env[model_name].search([
            ('ifs_company_id.company_id', '=', self.env.company.id)
        ]) if model_name else False
        return [
            ('id', 'in', invite_ids.filtered(
                lambda invite: invite.state != 'ready').mapped('factor_id').ids)
        ] if invite_ids else False

    def choice_factor(self):
        return self.env['ifs.gar.invite.' + self._context.get('invite_ifs_partner')].search([
            ('ifs_company_id.company_id', '=', self.env.company.id),
            ('factor_id', '=', self.factor_id.id)
        ]).start_entry()
