from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GuaranteeAccountsRecvChangePasswordTempToken(models.Model):
    _name = 'ifs.gar.change.password.temp.token'
    _inherit = ['uuid.short.mixin']
    _description = '修改支付密码临时token'
    
    merchant_code = fields.Char('付款方商编')
    token = fields.Char('订单token')
    expiration = fields.Datetime('token过期时间')
    token_valid = fields.Boolean(
        compute='_compute_token_valid', string='签名Token是否有效')
    
    @api.depends('token', 'expiration')
    def _compute_token_valid(self):
        dt = fields.Datetime.now()
        for sign_token in self:
            sign_token.token_valid = bool(sign_token.token) and \
                (not sign_token.expiration or dt <= sign_token.expiration)
                
    @api.model
    def create(self, vals):
        if 'token' not in vals:
            token = self.short_uuid4()
            while self.sign_with_token(token):
                token = self.short_uuid4()
            vals['token'] = token

        vals['expiration'] = fields.Datetime.now() + timedelta(hours=3)
        order = super(
            GuaranteeAccountsRecvChangePasswordTempToken, self).create(vals)

        return order
    
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