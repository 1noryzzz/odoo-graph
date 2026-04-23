# -*- coding: utf-8 -*-
import functools

from odoo import api


def model_callback(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        self = args[0]
        return func(
            *args, self._context.get('entry'),
            self._context.get('message'),
            self._context.get('callback_action'),
            self._context.get('callback_log'), **kw)

    return wrapper


api.model_callback = model_callback
