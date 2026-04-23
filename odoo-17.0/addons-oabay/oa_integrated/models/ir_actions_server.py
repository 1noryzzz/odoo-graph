# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    usage = fields.Selection(selection_add=[
        ('oa_callback', u'集成平台回调')], ondelete={'oa_callback': 'cascade'})
