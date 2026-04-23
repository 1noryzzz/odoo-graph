# -*- coding: utf-8 -*-

import logging
import oss2
import redis

from datetime import datetime, timedelta
from odoo import fields, models, api, tools
_logger = logging.getLogger(__name__)

DEFAULT_OSS_EXPIRED = 60 * 3


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    oss_bucket_name = fields.Char('OSS Bucket Name')
    oss_endpoint = fields.Char('OSS Endpoint')
    oss_endpoint_internal = fields.Char('OSS Endpoint Internal')
    oss_key = fields.Char('OSS File Key', index=True, unaccent=False)
    oss_url = fields.Char('OSS Url', index='btree_not_null', size=1024)
    oss_url_expiration = fields.Datetime(
        copy=False, string='OSS Url Expiration')

    # @api.model
    # def _get_storage_domain(self):
    #     # domain to retrieve the attachments to migrate
    #     return {
    #         'db': [('store_fname', '!=', False)],
    #         'file': [('db_datas', '!=', False)],
    #     }[self._storage()]

    @api.depends('store_fname', 'db_datas')
    def _compute_raw(self):
        for attach in self:
            if attach.store_fname:
                attach.raw = attach._file_read(attach.store_fname)
            elif 'oss_key' in self._fields and attach.oss_key and attach.oss_bucket_name:
                attach.raw = attach._oss_read(
                    attach.oss_key, attach.oss_bucket_name, attach.oss_endpoint_internal)
            else:
                attach.raw = attach.db_datas

    def unlink(self):
        to_delete_oss = set(
            '%s|%s|%s' % (
                attach.oss_key, attach.oss_bucket_name, attach.oss_endpoint_internal) for attach in self if attach.oss_key)
        res = super(IrAttachment, self).unlink()

        for oss_path in to_delete_oss:
            self._oss_delete(oss_path)

        return res

    def _retrieve_oss_auth(self):
        Config = self.env['ir.config_parameter'].sudo()
        access_key_id = Config.get_param(
            'galaxy.aliyun.access.key.id')
        access_secret = Config.get_param(
            'galaxy.aliyun.access.key.secret')

        return oss2.Auth(access_key_id, access_secret)

    def _retrieve_oss_bucket_obj(self, bucket_name, endpoint, auth=None):
        if not auth:
            auth = self._retrieve_oss_auth()
        return oss2.Bucket(auth, endpoint, bucket_name)

    def _mark_for_oss_gc(self, oss_path):
        connect_pool = redis.ConnectionPool(
            host=tools.config.get('redis_host', 'localhost'),
            port=int(tools.config.get('redis_port', 6379)),
            db=8,
            password=tools.config.get('redis_password', None))
        conn_redis = redis.StrictRedis(connection_pool=connect_pool)
        try:
            conn_redis.rpush('checklist', oss_path)
        except redis.ConnectionError:
            pass

    def _set_attachment_data(self, asbytes):
        for attach in self:
            oss_path = '%s|%s|%s' % (
                attach.oss_key, attach.oss_bucket_name, attach.oss_endpoint_internal) if attach.oss_key else False
            if oss_path:
                self._oss_delete(oss_path)

        super()._set_attachment_data(asbytes)

    def _is_bundle(self, mimetype):
        if mimetype in ['text/css', 'text/less', 'text/sass', 'text/scss', 'text/xml', 'application/json', 'application/javascript']:
            return True
        return False

    def _get_datas_related_values(self, data, mimetype, is_public=False):
        values = super()._get_datas_related_values(data, mimetype)
        Config = self.env['ir.config_parameter'].sudo()

        if data and self._storage() == 'oss':
            if self._is_bundle(mimetype):
                # 样式表放到阿里云OSS以后，会造成样式表内的静态资源（比如图片）的相对地址，变为阿里云的地址而无法使用
                # 所以在这里，所有的样式表都存到本地文件系统中
                values['store_fname'] = self._file_write(
                    data, values['checksum'])
                values['db_datas'] = False
            else:
                if is_public:
                    bucket_name = Config.get_param(
                        'galaxy.aliyun.oss.public.bucket', 'galaxy-pub')
                    endpoint = Config.get_param(
                        'galaxy.aliyun.oss.public.endpoint', 'oss-cn-shenzhen.aliyuncs.com')
                    endpoint_internal = Config.get_param(
                        'galaxy.aliyun.oss.public.endpoint.internal', 'oss-cn-shenzhen-internal.aliyuncs.com')
                else:
                    bucket_name = Config.get_param(
                        'galaxy.aliyun.oss.bucket', 'galaxy')
                    endpoint = Config.get_param(
                        'galaxy.aliyun.oss.endpoint', 'oss-cn-shenzhen.aliyuncs.com')
                    endpoint_internal = Config.get_param(
                        'galaxy.aliyun.oss.endpoint.internal', 'oss-cn-shenzhen-internal.aliyuncs.com')

                values['oss_bucket_name'] = bucket_name
                values['oss_endpoint'] = endpoint
                values['oss_endpoint_internal'] = endpoint_internal
                values['oss_key'] = self._oss_write(
                    data, values['checksum'], mimetype, values['oss_bucket_name'], values['oss_endpoint_internal'])
                values['db_datas'] = False
                values['store_fname'] = False

                if is_public:
                    values['oss_url'] = '//' + '/'.join(
                        ['.'.join([bucket_name, endpoint]), values['oss_key']])

        return values

    @api.model
    def _oss_read(self, fname, bucket_name, endpoint):
        bucket = self._retrieve_oss_bucket_obj(bucket_name, endpoint)
        try:
            return bucket.get_object(fname).read()
        except (IOError, OSError):
            _logger.info("_oss_read reading %s", fname, exc_info=True)
        except oss2.exceptions.AccessDenied:
            _logger.warning(
                "_oss_read access denied %s", fname, exc_info=True)
        return b''

    @api.model
    def _oss_write(self, bin_value, checksum, mimetype, bucket_name, endpoint):
        bucket = self._retrieve_oss_bucket_obj(bucket_name, endpoint)
        fname, full_path = self._get_path(bin_value, checksum)
        if not bucket.object_exists(fname):
            try:
                bucket.put_object(
                    fname, bin_value, headers={'Content-Type': mimetype})
            except IOError:
                _logger.info(
                    "_oss_write writing %s", fname, exc_info=True)
            except oss2.exceptions.AccessDenied:
                _logger.warning(
                    "_oss_write access denied %s", fname, exc_info=True)
        return fname

    @api.model
    def _oss_delete(self, oss_path):
        pass    # 暂时不清理OSS上的文件，因为数据库在共用数据库备份
        # self._mark_for_oss_gc(oss_path)

    @api.autovacuum
    def _gc_oss_store(self):
        """ Perform the garbage collection of the aliyun oss. """
        if self._storage() != 'oss':
            return

        cr = self._cr
        cr.commit()

        cr.execute("SET LOCAL lock_timeout TO '10s'")
        cr.execute("LOCK ir_attachment IN SHARE MODE")

        self._gc_oss_unsafe()

        # commit to release the lock
        cr.commit()

    def _gc_oss_unsafe(self):
        connect_pool = redis.ConnectionPool(
            host=tools.config.get('redis_host', 'localhost'),
            port=int(tools.config.get('redis_port', 6379)),
            db=8,
            password=tools.config.get('redis_password', None))
        conn_redis = redis.StrictRedis(connection_pool=connect_pool)
        checklist = {}
        removed = 0
        try:
            while True:
                oss_path = (conn_redis.lpop('checklist') or b'').decode('utf8')
                if oss_path == '':
                    break

                (oss_key, oss_bucket_name, oss_endpoint) = oss_path.split('|')
                checklist[oss_key] = {
                    'bucket': oss_bucket_name,
                    'endpoint': oss_endpoint
                }
            return  # 暂时不清理OSS上的文件，因为数据库在共用数据库备份
            auth = self._retrieve_oss_auth()
            for oss_keys in self.env.cr.split_for_in_conditions(checklist):
                # determine which files to keep among the checklist
                self.env.cr.execute(
                    "SELECT oss_key FROM ir_attachment WHERE oss_key IN %s", [oss_keys])
                whitelist = set(row[0] for row in self.env.cr.fetchall())

                # remove garbage oss obj
                for oss_key in oss_keys:
                    if oss_key not in whitelist:
                        oss_info = checklist.get(oss_key, {})
                        bucket = self._retrieve_oss_bucket_obj(
                            oss_info.get('bucket'), oss_info.get('endpoint'), auth)
                        if bucket.object_exists(oss_key):
                            try:
                                bucket.delete_object(oss_key)
                                removed += 1
                            except IOError:
                                _logger.info(
                                    "_oss_garbage %s", oss_key, exc_info=True)
                            except oss2.exceptions.AccessDenied:
                                _logger.info(
                                    "_oss_garbage access denied %s", oss_key, exc_info=True)
        except redis.ConnectionError:
            pass

        _logger.info("oss store gc %d checked, %d removed",
                     len(checklist), removed)

    def get_oss_url(self, content_type):
        if not self.oss_url or (self.oss_url_expiration and self.oss_url_expiration <= datetime.now()):
            bucket = self._retrieve_oss_bucket_obj(
                self.oss_bucket_name, self.oss_endpoint)
            headers = {}
            if content_type:
                headers = {'Content-type': content_type}
            self.oss_url = bucket.sign_url(
                'GET', self.oss_key, DEFAULT_OSS_EXPIRED, headers=headers, slash_safe=True)
            self.oss_url_expiration = datetime.now() + timedelta(seconds=DEFAULT_OSS_EXPIRED)
        return self.oss_url
