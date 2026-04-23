# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.http import request
import odoo
import psycopg2
from urllib.parse import urlparse

def is_redis_session_store_activated():
    return tools.config.get('redis_host')


try:
    import redis
except ImportError:
    if is_redis_session_store_activated():
        raise ImportError(
            'Please install package python3-redis: '
            'apt install python3-redis')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_galaxy_aliyun = fields.Boolean("阿里云服务")

    def _compute_db_list(self):
        try:
            dbs = odoo.service.db.list_dbs()
            return [(db,db) for db in dbs]
        except psycopg2.OperationalError:
            return []

    db_list = fields.Selection(selection=_compute_db_list,config_parameter='galaxy.db.list')
    set_default_db = fields.Boolean("设置默认数据库", default=False,config_parameter='galaxy.default.db')

    @api.onchange('db_list', 'set_default_db')
    def onchange_db(self):
        connect_pool = redis.ConnectionPool(
            host=tools.config.get('redis_host', 'localhost'),
            port=int(tools.config.get('redis_port', 6379)),
            db=8,
            password=tools.config.get('redis_password', None))
        conn_redis = redis.StrictRedis(connection_pool=connect_pool)
        try:
            if self.db_list:
                conn_redis.hset('db_monodb', urlparse(self.website_domain).netloc, self.db_list)
            if self.set_default_db:
                conn_redis.set('default_db_monodb',self.db_list)
        except redis.ConnectionError:
            pass