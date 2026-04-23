# coding=utf-8

import logging

_logger = logging.getLogger(__name__)


def work_autoreply_handler(request, msg):
    openid = msg.source
    if msg.id == request.entry.OPENID_LAST.get(openid):
        _logger.info('>>> 重复的微信消息')
        return ''
    request.entry.OPENID_LAST[openid] = msg.id
    return 'ok'
