# -*- coding: utf-8 -*-

import json

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        user = request.env.user
        session_info = super(Http, self).session_info()

        session_info.get('user_companies', {}).update({
            'allowed_companies': {
                comp.id: {
                    'id': comp.id,
                    'name': comp.name,
                    'sequence': comp.sequence,
                    'ifs_partners': comp.ifs_partners or [],
                } for comp in user.company_ids
            },
        })
        return session_info
