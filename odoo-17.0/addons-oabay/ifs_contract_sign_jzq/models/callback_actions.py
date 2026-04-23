# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OaCallbackActions(models.Model):
    _inherit = 'oa.callback.action'

    value_from = fields.Selection(selection_add=[
        ('jzq', u'君子签'),
    ], ondelete={'jzq': 'cascade'})
