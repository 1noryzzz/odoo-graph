# -*- coding: utf-8 -*-

import logging


from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def default_get(self, fields):
        vals = super(ResCompany, self).default_get(fields)
        vals.update({
            'country_id': self.env.company.country_id.id,
            'state_id': self.env.company.state_id.id,
            'website': 'https://www.liefwiz.cn',
        })
        return vals

    area_id = fields.Many2one(
        'res.country.area', compute='_compute_address', inverse='_inverse_area',
        string="行政区", domain="[('state_id', '=?', state_id)]"
    )

    # 一般的情况下，负责人要求与法人是同一人
    legal_id = fields.Many2one(
        'res.partner', string='法人', ondelete='restrict',
        domain="[('is_company', '=', False), '|', ('parent_id', '=', False), ('parent_id', '=', partner_id)]")
    principal_id = fields.Many2one(
        'res.partner', string='负责人', ondelete='restrict',
        domain="[('is_company', '=', False), '|', ('parent_id', '=', False), ('parent_id', '=', partner_id)]")

    acquiescence_bank_id = fields.Many2one(
        'res.partner.bank', string='默认银行账号', compute='_compute_acquiescence_bank_id')

    def _get_company_address_field_names(self):
        return super()._get_company_address_field_names() + ['area_id']

    def _inverse_area(self):
        for company in self:
            company.partner_id.area_id = company.area_id

    @api.depends('bank_ids')
    def _compute_acquiescence_bank_id(self):
        for record in self:
            record.acquiescence_bank_id = record.bank_ids and record.bank_ids[0] or False


class ResPartner(models.Model):
    _inherit = 'res.partner'

    _rec_names_search = ['display_name', 'email', 'phone', 'mobile']
