# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingPartnerFactor(models.Model):
    _name = 'ifs.partner.factor'
    _inherit = ['ifs.partner.factor', 'uuid.short.mixin']

    supplier_ids = fields.One2many(
        'ifs.gar.partner.factor.supplier', 'factor_id', string='与供应方的合作关系')
    merchant_ids = fields.One2many(
        'ifs.gar.partner.factor.merchant', 'factor_id', string='与采购方的合作关系')
    franchisee_ids = fields.One2many(
        'ifs.gar.partner.factor.franchisee', 'factor_id', string='与合伙人的合作关系')
    lawfirm_ids = fields.One2many(
        'ifs.gar.partner.factor.lawfirm', 'factor_id', string='与律师事务所的合作关系')

    signature = fields.Image(
        '保理方签名', copy=False,
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
                '/partner/factor/sign?token=',
                sign_token.token
            ])

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
            'name': '更新保理方存留签名',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'ifs.partner.factor.sign.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_factor_id': self.id,
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
