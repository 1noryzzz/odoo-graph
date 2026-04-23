# -*- coding: utf-8 -*-

import logging
from contextlib import contextmanager

import happybase
import records
import redis
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from pymongo import MongoClient
from urllib import parse

_logger = logging.getLogger(__name__)

_RecordDataBase = {}


class ExternalDbsource(models.Model):
    """ 
    通过Records 库，连接外部数据源
    """
    _name = "base.external.dbsource"
    _description = "External Database Sources"

    CONNECTORS = [("postgresql", "PostgreSQL"), ('mysql', 'MySQL'),
                  ('sqlite', 'SQLite'), ('oracle', 'ORACLE'),
                  ('mssql', 'Microsoft SQL Server'), ('redis', 'Redis'),
                  ('mongodb', 'MongoDB'), ('hbase', 'HBase')]
    name = fields.Char("数据源名称", required=True, size=64)
    conn_string = fields.Text(
        "连接字符串",
        help="""
    Sample connection strings:
            数据库类型 + 数据库驱动 :// 数据库用户名 : 数据库密码 @ IP地址 : 端口号 / 数据库
    - MySQL: mysql+pymysql://user:%s@server:port/dbname
    """,
    )
    pool_size = fields.Integer("连接池大小", default=5)
    max_overflow = fields.Integer("连接池最大溢出大小", default=10)
    timeout = fields.Float("超时时间", default=30.0)
    conn_string_full = fields.Text(readonly=True,
                                   compute="_compute_conn_string_full")
    password = fields.Char("密码", size=40)
    connector = fields.Selection(
        CONNECTORS,
        "连接类型",
        required=True,
        help="If a connector is missing from the list, check the server "
        "log to confirm that the required components were detected.",
    )

    @api.depends("conn_string", "password")
    def _compute_conn_string_full(self):
        for record in self:
            if record.password and "%s" in record.conn_string:
                record.conn_string_full = record.conn_string % parse.quote_plus(record.password)
            else:
                record.conn_string_full = record.conn_string

    def connection_close(self, db):
        return db.close()

    @contextmanager
    def connection_open(self):
        # self.ensure_one()
        global _RecordDataBase

        in_pool = False
        try:
            in_pool = True
            db = _RecordDataBase.get(self.id)
            if type(db) == redis.ConnectionPool or self.connector == 'redis':
                if not db:
                    db = eval('redis.ConnectionPool(%s)' % self.conn_string_full)
                    _RecordDataBase[self.id] = db
                    
                db = redis.StrictRedis(connection_pool=db)
            elif not db:
                if self.connector == 'mongodb':
                    kwargs = {}
                    if self.pool_size:
                        kwargs['minPoolSize'] = self.pool_size
                    if self.max_overflow:
                        kwargs['maxPoolSize'] = self.max_overflow
                        
                    db = MongoClient(self.conn_string_full, **kwargs)
                elif self.connector == 'hbase':
                    db = eval('happybase.ConnectionPool(size=self.pool_size, %s)' % self.conn_string_full)
                else:
                    kwargs = {}
                    if self.pool_size:
                        kwargs['pool_size'] = self.pool_size
                    if self.max_overflow:
                        kwargs['max_overflow'] = self.max_overflow
                    # if self.timeout:
                    #     kwargs['timeout'] = self.timeout
                    db = records.Database(self.conn_string_full, **kwargs)
                    #TODO: start a transation
                    
                _RecordDataBase[self.id] = db
            yield db
        finally:
            try:
                if not in_pool:
                    self.connection_close(db)

                #TODO: commit a transation
            except Exception:
                _logger.exception("Connection close failure.")

    def connection_test(self):
        """ It tests the connection

        Raises:
            ValidationError: On connection failed
        """
        try:
            with self.connection_open() as db:
                if self.connector == 'redis':
                    db.ping()
                elif self.connector == 'mongodb':
                    db.admin.command('ismaster')
                elif self.connector == 'hbase':
                    pass
                else:
                    db.query('SELECT 1;')
        except Exception as e:
            raise ValidationError(_("连接失败:\n" "具体信息如下:\n%s") % tools.ustr(e))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("数据库连接成功"),
                # 'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def write(self, data):
        res = super(ExternalDbsource, self).write(data)
        if self.id in _RecordDataBase:
            if self.connector not in ('hbase', 'redis'):
                _RecordDataBase.pop(self.id).close()
            else:
                _RecordDataBase.pop(self.id)
        return res
