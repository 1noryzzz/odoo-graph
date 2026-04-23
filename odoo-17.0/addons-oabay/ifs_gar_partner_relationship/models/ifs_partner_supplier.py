# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingPartnerSupplier(models.Model):
    _name = 'ifs.partner.supplier'
    _inherit = ['ifs.partner.supplier', 'uuid.short.mixin']

    factor_ids = fields.One2many(
        'ifs.gar.partner.factor.supplier', 'supplier_id', string='与保理方的合作关系')
    merchant_ids = fields.One2many(
        'ifs.gar.partner.supplier.merchant', 'supplier_id', string='与采购方的合作关系')

    merchant_count = fields.Integer(
        '关联采购方数', compute='_compute_merchant_count')

    signature = fields.Image(
        '供应方签名', copy=False,
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
                '/partner/supplier/sign?token=',
                sign_token.token
            ])

    @api.depends('merchant_ids')
    def _compute_merchant_count(self):
        for record in self:
            record.merchant_count = 0
            if record.merchant_ids:
                ready_merchant_ids = record.merchant_ids.filtered(
                    lambda m: m.merchant_id.state == 'normal')
                record.merchant_count = len(ready_merchant_ids.ids)

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

    def create_or_update_sign(self):
        self._prepare_sign(sign_name=self.ifs_company_id.legal_id.name)
        return {
            'name': '更新供应方存留签名',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'ifs.partner.supplier.sign.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_supplier_id': self.id,
                'default_sign_url': self.sign_url,
            }
        }

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
