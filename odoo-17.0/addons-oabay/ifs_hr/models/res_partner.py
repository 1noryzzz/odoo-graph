import random

from odoo import api, exceptions, fields, models, _


def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = '0123456789'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(6))


class ResPartner(models.Model):
    _inherit = 'res.partner'

    default_pwd = fields.Char('默认密码')

    def signup_prepare(self, signup_type="signup", expiration=False):
        for partner in self:
            if expiration or not partner.signup_valid:
                token = random_token()
                while self._signup_retrieve_partner(token):
                    token = random_token()
                partner.write(
                    {'signup_token': token, 'signup_type': signup_type, 'signup_expiration': expiration})
        return True
