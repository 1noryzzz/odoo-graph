# -*- coding: utf-8 -*-

import logging

from . import galaxy_open_api_app
from datetime import datetime, timedelta
from odoo import api, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class APIKeys(models.Model):
    _inherit = 'res.users.apikeys'

    # 回收scope 是 galaxy.open.api的key
    @api.autovacuum
    def _gc_invalid_keys(self):
        timeout_ago = datetime.utcnow() - timedelta(
            seconds=galaxy_open_api_app.EXPIRES_IN + galaxy_open_api_app.SAFE_GAP)
        domain = [
            ('scope', '=', 'galaxy.open.api'),
            ('create_date', '<', timeout_ago.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT))]
        return self.sudo().search(domain).unlink()
