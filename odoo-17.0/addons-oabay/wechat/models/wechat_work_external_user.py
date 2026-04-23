# -*- coding: utf-8 -*-

import base64
import logging

import requests
from odoo import fields, models
from wechatpy.exceptions import WeChatClientException

from ..rpc import work_entry

_logger = logging.getLogger(__name__)


def get_img_data(pic_url):
    headers = {
        'Accept': 'textml,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
        'Cache-Control': 'no-cache',
        'Host': 'wx.qlogo.cn',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    r = requests.get(pic_url, headers=headers, timeout=50)
    return r.content


class WorkExternalUser(models.Model):

    _name = 'wechat.work.external.user'
    _description = 'Work External Users'
    _inherit = ['wechat.user.mixin']
    _order = 'id desc'

    work_id = fields.Many2one(
        'wechat.work.config', required=True, string='Wechat Work', ondelete='cascade')
    user_type = fields.Char('User Type')
    position = fields.Char('User Position')
    corp_name = fields.Char('Corpration Name')
    corp_full_name = fields.Char('Corpration Full Name')

    work_user_follow_ids = fields.One2many(
        'wechat.work.external.user.follow', 'external_user_id', string='Work Users', auto_join=True)

    _sql_constraints = [(
        'work_external_user_open_id_unique',
        'UNIQUE (work_id, open_id)',
        'Work external user open_id with work_id is existed！'
    )]

    def _parse_values(self, values):
        if 'external_userid' in values:
            values['open_id'] = values['external_userid']
        if 'unionid' in values:
            values['union_id'] = values['unionid']
        if 'name' in values:
            values['nickname'] = values['name']
        if 'type' in values:
            values['user_type'] = values['type']
        if 'gender' in values:
            if values['gender'] == 1:
                values['gender'] = 'male'
            elif values['gender'] == 2:
                values['gender'] = 'female'
            else:
                values['gender'] = 'other'
        if values['avatar'] != None and values['avatar'].startswith('http'):
            values['avatar_url'] = values['avatar']
            try:
                values['image_1920'] = base64.encodebytes(
                    get_img_data(values['avatar_url']))
            except:
                _logger.error('external_userid %s get img data error' %
                              values['open_id'])
        values['type'] = 'contact'
        values['lang'] = 'zh_CN'  # values['language']
        values['tz'] = 'Asia/Shanghai'

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def signup(self, wechat_work, external_user_info):
        external_user = False
        if external_user_info.get('errcode') == 0:
            info = self._parse_values(
                external_user_info.get('external_contact'))

            external_user = self.search(
                ['&', ('open_id', '=', info.get('open_id')),
                 ('work_id.id', '=', wechat_work.id)], limit=1)
            if not external_user.exists():
                partner = self.env['res.partner'].search(
                    [('union_id', '!=', False), ('union_id', '=', info.get('union_id'))], limit=1)

                if not partner.exists():
                    signup_vals = {
                        'login': '_'.join([
                            self.env.cr.dbname,
                            str(wechat_work.company_id.id),
                            'work_ext',
                            (info.get('union_id') or (
                                '%s_%d' % (info.get('open_id'), wechat_work.id)))]),
                        'email': '%s@work_ext' % (info.get('union_id') or (
                            '%s_%d' % (info.get('open_id'), wechat_work.id))),
                        'name': info.get('name'),
                        'company_id': wechat_work.company_id.id,
                        'company_ids': [(6, 0, [wechat_work.company_id.id])],
                        'livechat_username': info.get('nickname'),
                    }

                    db, login, password = self.env['res.users'].signup(
                        signup_vals)
                    _logger.info('db = %s, login = %s' % (db, login))

                    user = self.env['res.users'].search(
                        [('login', '=', signup_vals.get('login'))], limit=1)

                    info['partner_id'] = user.partner_id.id
                else:
                    info['partner_id'] = partner.id

                info['work_id'] = wechat_work.id
                try:
                    external_user = self.create(info)
                except:
                    info.pop('image_1920')
                    external_user = self.create(info)
            else:
                try:
                    external_user.write(info)
                except:
                    info.pop('image_1920')
                    external_user.write(info)

        return external_user

    def sync(self, wechat_work, work_user):
        entry = work_entry.retrieve_entry(self.env, wechat_work.corp_id)
        if entry.ext_contacts_client:
            try:
                ext_info = entry.ext_contacts_client.external_contact.list(
                    work_user.work_userid)
                if ext_info.get('errcode') == 0:
                    external_userids = ext_info.get('external_userid')
                    for ext_uid in external_userids:
                        external_user_info = entry.ext_contacts_client.external_contact.get(
                            ext_uid)
                        external_user = self.signup(
                            wechat_work, external_user_info)

                        follow_user = external_user_info.get('follow_user', [])
                        if external_user and len(follow_user) > 0:
                            self.env['wechat.work.external.user.follow'].update_from_wework(
                                work_user, external_user.id, follow_user)
            except WeChatClientException as e:
                _logger.error("Sync external user has some error: %s", repr(e))
