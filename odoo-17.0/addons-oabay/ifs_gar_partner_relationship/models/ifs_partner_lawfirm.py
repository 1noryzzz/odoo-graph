# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerLawFirm(models.Model):
    _inherit = 'ifs.partner.lawfirm'

    factor_ids = fields.One2many(
        'ifs.gar.partner.factor.lawfirm', 'lawfirm_id', string='与保理方的合作关系')

    # @override from current.company.partner.mixin
    # def _compute_partner_related(self):
    #     for record in self:
    #         record.partner_related = ''
    #         if self.env.company.ifs_partner == 'factor':
    #             if record.factor_ids.filtered(
    #                     lambda factor_lawfirm: factor_lawfirm.factor_id.business_id.company_id.id == self.env.company.id).exists():
    #                 record.partner_related = 'factor-law-firm'

    # def _create_or_update_relationship(self, lawfirm, vals):
    #     if self.env.company.ifs_partner == 'factor':
    #         inner_vals = {}
    #         for k, v in vals.items():
    #             if k in self.env['ifs.gar.partner.factor.lawfirm']._fields:
    #                 inner_vals[k] = v

    #         is_exist = False
    #         factor_lawfirm = False
    #         if lawfirm.factor_ids.exists():
    #             factor_lawfirm = lawfirm.factor_ids.filtered(
    #                 lambda factor_lawfirm: factor_lawfirm.factor_id.business_id.company_id.id == self.env.company.id)
    #             if factor_lawfirm.exists():
    #                 factor_lawfirm.write(inner_vals)
    #                 is_exist = True

    #         factor = self.env['ifs.partner.factor'].search(
    #             [('business_id.company_id', '=', self.env.company.id)])
    #         if not is_exist and factor.exists():
    #             inner_vals.update({
    #                 'factor_id': factor.id,
    #                 'lawfirm_id': lawfirm.id,
    #             })
    #             factor_lawfirm = self.env['ifs.gar.partner.factor.lawfirm'].create(
    #                 inner_vals)

    # @api.model
    # def create(self, vals):
    #     lawfirm = super(
    #         InclusiveFinancingPartnerLawFirm, self).create(vals)
    #     self._create_or_update_relationship(lawfirm, vals)
    #     return lawfirm

    # def write(self, vals):
    #     rst = super(InclusiveFinancingPartnerLawFirm, self).write(vals)
    #     self._create_or_update_relationship(self, vals)
    #     return rst
