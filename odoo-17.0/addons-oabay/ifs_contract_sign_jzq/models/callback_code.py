# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OACallbackCode(models.Model):
    _inherit = 'oa.callback.code'
    
    ValueType = [
        ('organization', '企业实名认证'),
        ('sign', '签约'),
    ]

    value_from = fields.Selection(selection_add=[
        ('jzq', u'君子签'),
    ], ondelete={'jzq': 'cascade'})
    value_type = fields.Selection(selection_add=ValueType)