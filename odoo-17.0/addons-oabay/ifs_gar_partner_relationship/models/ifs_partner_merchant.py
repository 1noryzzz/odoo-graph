# -*- coding: utf-8 -*-

from collections import OrderedDict
from datetime import timedelta

from odoo import _, api, models, fields
from odoo.osv import expression
from odoo.exceptions import UserError


class InclusiveFinancingPartnerMerchant(models.Model):
    _name = 'ifs.partner.merchant'
    _inherit = ['ifs.partner.merchant', 'uuid.short.mixin']

    factor_ids = fields.One2many(
        'ifs.gar.partner.factor.merchant', 'merchant_id', string='与保理方的合作关系')
    supplier_ids = fields.One2many(
        'ifs.gar.partner.supplier.merchant', 'merchant_id', string='与供应方的合作关系')

    supplier_names = fields.Char('供应方名称', compute='_compute_supplier_names')

    signature = fields.Image(
        '采购方签名', copy=False,
        attachment=True, max_width=1024, max_height=1024)
    sign_name = fields.Char('签名人')
    token = fields.Char(copy=False)
    expiration = fields.Datetime(copy=False)
    token_valid = fields.Boolean(
        compute='_compute_token_valid', string='签名Token是否有效')
    sign_url = fields.Char(
        '手写签名地址', compute='_compute_sign_url')

    @api.depends('token', 'expiration')
    def _compute_token_valid(self):
        dt = fields.Datetime.now()
        for sign_token in self:
            sign_token.token_valid = bool(sign_token.token) and \
                (not sign_token.expiration or dt <= sign_token.expiration)

    @api.depends('token')
    def _compute_sign_url(self):
        for sign_token in self:
            sign_token.sign_url = ''.join([
                self.env['ir.config_parameter'].sudo(
                ).get_param('web.base.url'),
                '/partner/merchant/sign?token=',
                sign_token.token
            ])

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name == 'supplier_ids':
            enable_counters = kwargs.get('enable_counters', False)
            records = self.env['ifs.partner.supplier'].search_read(
                [], ['display_name'], order="seq_code asc")

            values_range = OrderedDict()
            for record in records:
                record_id = record['id']
                if enable_counters:
                    model_domain = expression.AND([
                        kwargs.get('search_domain', []),
                        kwargs.get('category_domain', []),
                        kwargs.get('filter_domain', []),
                        [('supplier_ids.supplier_id', '=', record_id)]
                    ])
                    record['__count'] = self.env['ifs.partner.merchant'].search_count(
                        model_domain)
                values_range[record_id] = record

            return {
                # 'parent_field': 'supplier_ids.supplier_id',
                'values': list(values_range.values()),
            }

        return super().search_panel_select_range(field_name, **kwargs)

    @api.depends('supplier_ids')
    def _compute_supplier_names(self):
        for record in self:
            suppliers = []
            supplier_ids = self.env['ifs.partner.supplier'].search(
                [('id', 'in', record.supplier_ids.supplier_id.ids)])
            supplier_merchant = record.supplier_ids.filtered(
                lambda x: x.supplier_id.id in supplier_ids.ids)
            if record.supplier_ids:
                suppliers += supplier_merchant.mapped(
                    'supplier_id.name') if supplier_merchant else False

            record.supplier_names = ','.join(suppliers)

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        for expression in domain:
            if expression[0] == 'supplier_ids' and expression[1] == '=':
                expression[0] = 'supplier_ids.supplier_id'

        return super().search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        for expression in domain:
            if expression[0] == 'supplier_ids' and expression[1] == '=':
                expression[0] = 'supplier_ids.supplier_id'

        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def _prepare_sign(self, sign_name=False, expiration=False):
        sign_name = sign_name or self.env.user.name
        token = self.short_uuid4()
        expiration = expiration or (fields.Datetime.now() + timedelta(hours=1))
        while self.sign_with_token(token):
            token = self.short_uuid4()

        self.write({
            'token': token,
            'sign_name': sign_name,
            'expiration': expiration,
        })

    def generate_sign_url(self):
        self._prepare_sign(sign_name=self.ifs_company_id.legal_id.name)

        return self.sign_url

    def sign_with_token(self, token, check_validity=False, raise_exception=False):
        sign_token = self.search([('token', '=', token)], limit=1)
        if not sign_token:
            if raise_exception:
                raise UserError(_("签名参数无效"))
            return False
        if check_validity and not sign_token.token_valid:
            if raise_exception:
                raise UserError(_("签名Token过期"))
            return False
        return sign_token
