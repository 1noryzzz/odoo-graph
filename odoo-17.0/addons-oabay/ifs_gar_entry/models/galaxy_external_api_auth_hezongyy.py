# -*- coding: utf-8 -*-

import time
import hashlib

from odoo import fields, models, _

class GalaxyExternalApiDisableWarnings(models.Model):
    _name = 'galaxy.external.api.auth.hezongyy'
    _inherit = ['galaxy.external.api.auth']
    _description = '合纵认证'
    
    def do_auth(self, headers=None, query=None, body=None,rargs=None):
        super().do_auth(headers, query, body,rargs)
        cfg = self.env['ir.config_parameter'].sudo()
        secretKey = cfg.get_param('ifs.gar.entry.hezongyy.secret.key', '')
        systemtimestamp  = int(time.time()) 
        systemsign = hashlib.sha1(f'{systemtimestamp}{secretKey}'.encode('utf-8')).hexdigest()
        headers.update({
            'systemtimestamp':str(systemtimestamp),
            'systemsign':systemsign.upper()
        })


class GalaxyExternalApi(models.Model):
    _inherit = 'galaxy.external.api'

    request_auth = fields.Reference(selection_add=[
        ('galaxy.external.api.auth.hezongyy', '合纵认证'),
    ], string='认证方式')