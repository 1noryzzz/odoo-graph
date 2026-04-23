# -*- coding: utf-8 -*-
import functools

from odoo import api


def threading(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        self = args[0]
        with api.Environment.manage():
            with self.pool.cursor() as new_cr:
                new_cr.autocommit(True)
                self = self.with_env(self.env(cr=new_cr))
                new_args = [self, ]
                if len(args) > 1:
                    new_args += list(args)[1:]
                return func(*new_args, **kw)

    return wrapper


api.threading = threading
