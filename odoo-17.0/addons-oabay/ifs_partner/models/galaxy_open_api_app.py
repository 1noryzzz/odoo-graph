# -*- coding: utf-8 -*-

import logging

from datetime import timedelta
from odoo import _, api, models, fields, http
from cache_base import retrieve_cache_base

_logger = logging.getLogger(__name__)


class GalaxyOpenApiApp(models.Model):
    _inherit = 'galaxy.open.api.app'

    owner_id = fields.Reference(
        selection_add=[('ifs.partner.supplier', '供应方')])

    @api.onchange('owner_id')
    def _onchange_owner_id(self):
        if self.owner_id and self.owner_id._name == 'ifs.partner.supplier':
            self.company_id = self.owner_id.company_id
            self.user_id = self.owner_id.root_employee_id.user_id
        else:
            self.company_id = False
            self.user_id = False
