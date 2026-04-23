# coding=utf-8

import json
import logging
import time
import traceback

from odoo import tools
from wechatpy.session import SessionStorage
from wechatpy.utils import to_text

_logger = logging.getLogger(__name__)


class EntryBase(object):
    def __init__(self, dbname, app_id):
        self.dbname = dbname
        self.app_id = app_id
        self.OPENID_LAST = {}
        
    def _get_path(self, key):
        data_dir = tools.config['data_dir']
        cls_name = self.__class__.__name__

        return '%s/%s-%s/%s-%s' % (data_dir, cls_name, key, self.dbname, self.app_id)
        
    def init_data(self):
        pass
        # from diskcache import Index
        #self.UUID_OPENID = Index(self._get_path('UUID_OPENID'))
        #self.OPENID_UUID = Index(self._get_path('OPENID_UUID'))
        # self.OPENID_LAST = Index(self._get_path('OPENID_LAST'))

    def gen_session(self):
        return SessionStorage(self.dbname)


class SessionStorage(SessionStorage):
    def __init__(self, dbname):
        self.file_dir = '%s/%s' % (tools.config['data_dir'], dbname)

    def get(self, key, default=None):
        try:
            with open('%s-%s' % (self.file_dir, key), 'r') as f:
                _dict = json.loads(to_text(f.read()))
                timestamp = time.time()
                expires_at = _dict.get('expires_at', 0)
                if expires_at == 0 or expires_at - timestamp > 60:
                    return _dict['val']
        except:
            traceback.print_exc()
            return default

    def set(self, key, value, ttl=None):
        if value is None:
            return
        with open('%s-%s' % (self.file_dir, key), 'w') as f:
            value = json.dumps(
                {'val': value, 'expires_at': ttl and int(time.time()) + ttl or 0})
            f.write(value)

    def delete(self, key):
        self.set(key, '')
