# -*- coding: utf-8 -*-


from odoo import api, models
from passlib.context import CryptContext


# API keys support
API_KEY_SIZE = 20  # in bytes
INDEX_SIZE = 8  # in hex digits, so 4 bytes, or 20% of the key
KEY_CRYPT_CONTEXT = CryptContext(
    # default is 29000 rounds which is 25~50ms, which is probably unnecessary
    # given in this case all the keys are completely random data: dictionary
    # attacks on API keys isn't much of a concern
    ['pbkdf2_sha512'], pbkdf2_sha512__rounds=6000,
)


class APIKeys(models.Model):
    _inherit = 'res.users.apikeys'

    def _check_credentials(self, *args, scope, key):
        assert scope, "scope is required"
        if len(args) == 2 and args[0] == 'galaxy_token':
            index = key[:INDEX_SIZE]
            self.env.cr.execute('''
                SELECT user_id, key
                FROM {} INNER JOIN res_users u ON (u.id = user_id)
                WHERE u.active and index = %s AND (scope IS NULL OR scope = %s) AND name = %s
            '''.format(self._table),
                [index, scope, args[1]])
            for user_id, current_key in self.env.cr.fetchall():
                if KEY_CRYPT_CONTEXT.verify(key, current_key):
                    return user_id
        else:
            return super()._check_credentials(*args, scope=scope, key=key)
