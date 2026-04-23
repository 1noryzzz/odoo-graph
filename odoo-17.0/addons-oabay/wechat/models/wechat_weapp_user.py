# -*- coding: utf-8 -*-

import base64
import json
import logging

import requests
from odoo import api, fields, models
from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)


def get_img_data(pic_url):
    headers = {
        'Accept': 'textml,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
        'Cache-Control': 'no-cache',
        'Host': 'mmbiz.qpic.cn',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    r = requests.get(pic_url, headers=headers, timeout=50)
    return r.content


class WeappUser(models.Model):
    _name = 'wechat.weapp.user'
    _description = 'WeApp Users'
    _inherit = ['wechat.user.mixin']
    _order = 'id desc'

    weapp_id = fields.Many2one(
        'wechat.weapp.config', required=True, string='Wechat Weapp', ondelete='cascade')

    _sql_constraints = [(
        'weapp_user_open_id_unique',
        'UNIQUE (weapp_id, open_id)',
        'WeApp user open_id with weapp_id is existed！'
    )]

    def _parse_values(self, values, phone_info):
        country = None

        if 'openId' in values:
            values['open_id'] = values['openId']
        if 'unionId' in values:
            values['union_id'] = values['unionId']
        if 'nickName' in values:
            values['name'] = values['nickName']
            values['nickname'] = values['nickName']
        if 'language' in values:
            values['lang'] = 'zh_CN'  # values['language']
            values['tz'] = 'Asia/Shanghai'
        if 'gender' in values:
            if values['gender'] == 1:
                values['gender'] = 'male'
            elif values['gender'] == 2:
                values['gender'] = 'female'
            else:
                values['gender'] = 'other'
        if 'country' in values:
            country = self.env['res.country'].with_context(lang='zh_CN').search(
                [('name', '=', values['country'])], limit=1)
            if not country.exists():
                country = self.env['res.country'].with_context(lang='en_US').search(
                    [('name', '=', values['country'])], limit=1)
            if country.exists():
                values['country_id'] = country.id
                if 'province' in values:
                    province = self.env['res.country.state'].with_context(lang='zh_CN').search(
                        ['&', ('country_id', '=', country.id),
                         ('name', '=like', values['province'] + '%')],
                        limit=1
                    )
                    if not province.exists():
                        province = self.env['res.country.state'].with_context(lang='en_US').search(
                            ['&', ('country_id', '=', country.id),
                             ('name', '=like', values['province'] + '%')],
                            limit=1
                        )
                    if province.exists():
                        values['state_id'] = province.id

        if values['avatarUrl'] != None and values['avatarUrl'].startswith('http'):
            values['avatar_url'] = values['avatarUrl']
            try:
                values['image_1920'] = base64.encodebytes(
                    get_img_data(values['avatarUrl']))
            except:
                _logger.error('openid %s get img data error' %
                              values['open_id'])
        values['type'] = 'contact'

        if 'phoneNumber' in phone_info and phone_info['phoneNumber'].strip() != '':
            values['mobile'] = phone_validation.phone_format(
                phone_info['phoneNumber'], country)

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    @api.model
    def signup(self, weapp_config, session_wizard):
        user_info = json.loads(session_wizard.user_info)
        phone_info = json.loads(session_wizard.phone_info)

        info = self._parse_values(user_info, phone_info)
        weapp_user = self.search(
            [('open_id', '=', info.get('open_id'))], limit=1)
        if not weapp_user.exists():
            partner = self.env['res.partner'].search(
                [('mobile', '=', info.get('mobile'))], limit=1)
            if not partner.exists():
                signup_vals = {
                    'login': '_'.join([self.env.cr.dbname, 'weapp', info.get('mobile')]),
                    'email': '%s@weapp' % info.get('mobile'),
                    'name': info.get('name'),
                    'mobile': info.get('mobile'),
                    'company_id': weapp_config.website_id.company_id.id,
                    'company_ids': [(6, 0, [weapp_config.website_id.company_id.id])],
                    'livechat_username': info.get('nickname'),
                }

                db, login, password = self.env['res.users'].signup(signup_vals)
                _logger.info('db = %s, login = %s' % (db, login))

                partner = self.env['res.partner'].search(
                    [('mobile', '=', info.get('mobile'))], limit=1)
            else:
                exist_user = self.env['res.users'].search(
                    [('partner_id', '=', partner.id)], limit=1)
                exist_user.write({
                    'company_ids': [(4, weapp_config.website_id.company_id.id)]
                })
                info.pop('name')
                if partner.image_1920 and 'image_1920' in info:
                    info.pop('image_1920')
            info.update({
                'partner_id': partner.id,
                'weapp_id': weapp_config.id,
            })
            self.create(info)
        else:
            info.pop('name')
            if weapp_user.image_1920 and 'image_1920' in info:
                info.pop('image_1920')
            weapp_user.write(info)

    @api.model
    def read_to_weapp(self):
        self.ensure_one()
        return {
            "openId": self.open_id,
            "nickName": self.nickname,
            "gender": int(self.gender),
            "language": self.lang,
            "city": self.city,
            "province": self.state_id.name,
            "country": self.country_id.name,
            "avatarUrl": self.avatar_url,
            'is_registed': True
        }
