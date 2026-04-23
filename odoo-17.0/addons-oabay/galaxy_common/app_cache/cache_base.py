# coding=utf-8

import logging

_logger = logging.getLogger(__name__)

AppCacheDict = {}


class CacheBase(object):
    def __init__(self, dbname, rdbname):
        self.dbname = dbname
        self.rdbname = rdbname
        self.redis_db = False

    def init(self, env):
        global AppCacheDict

        entry_name = '-'.join([
            self.dbname, self.rdbname
        ])

        if entry_name in AppCacheDict:
            del AppCacheDict[entry_name]
        AppCacheDict[entry_name] = self

        self.redis_db = env['base.external.dbsource'].search(
            [('name', '=', self.rdbname)])


def retrieve_cache_base(env, rdbname):
    entry_name = '-'.join([
        env.cr.dbname, rdbname
    ])

    if entry_name not in AppCacheDict:
        CacheBase(env.cr.dbname, rdbname).init(env)

    return AppCacheDict[entry_name]
