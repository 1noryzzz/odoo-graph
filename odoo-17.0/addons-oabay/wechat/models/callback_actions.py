# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OaCallbackActions(models.Model):
    _inherit = 'oa.callback.action'

    value_from = fields.Selection(selection_add=[
        ('wechat', u'微信公众号'), ('wework', u'企业微信')
    ], ondelete={'wechat': 'cascade', 'wework': 'cascade'})
