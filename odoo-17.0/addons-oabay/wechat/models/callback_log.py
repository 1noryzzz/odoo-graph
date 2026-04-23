# -*- coding: utf-8 -*-

import logging

from odoo import models
from wechatpy.messages import TextMessage, ImageMessage, LocationMessage, LinkMessage
from wechatpy.events import SubscribeEvent, SubscribeScanEvent, ScanEvent


class OACallbackLog(models.Model):
    _inherit = 'oa.callback.log'

    def _get_msg_body(self, message):
        if isinstance(message, TextMessage):
            return message.content
        elif isinstance(message, ImageMessage):
            return message.image
        elif isinstance(message, LocationMessage):
            return ','.join([message.location_x, message.location_y])
        elif isinstance(message, LinkMessage):
            return '%s:%s(%s)' % (message.title, message.description, message.url)
        elif isinstance(message, SubscribeEvent):
            return message.key
        elif isinstance(message, SubscribeScanEvent) or isinstance(message, ScanEvent):
            return ','.join([message.scene_id, message.ticket])

        return super(OACallbackLog, self)._get_msg_body(message)
