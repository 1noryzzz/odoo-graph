# -*- coding: utf-8 -*-

import base64
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
        'Host': 'wework.qpic.cn',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    r = requests.get(pic_url, headers=headers, timeout=50)
    return r.content


class WorkUser(models.Model):

    _name = 'wechat.work.user'
    _description = 'Wechat Work Users'
    _inherits = {'res.users': 'user_id'}
    _order = 'id desc'

    work_id = fields.Many2one(
        'wechat.work.config', required=True, string='Wechat Work', ondelete='cascade')
    work_userid = fields.Char('Wechat Work UserId', required=True)
    open_userid = fields.Char('Wechat Work Open UserId')
    name = fields.Char(related='user_id.name',
                       string='Name', inherited=True)
    alias = fields.Char('Alias')
    status = fields.Integer('Status')
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', auto_join=True,
                              string='Related Users', help='User data')
    avatar_url = fields.Char('Avatar Url')
    address = fields.Char('Address')
    qr_code = fields.Char('Qr Code Url')

    work_external_user_follow_ids = fields.One2many(
        'wechat.work.external.user.follow', 'work_user_id', string='Work External User Followers', auto_join=True)

    _sql_constraints = [(
        'userid_unique',
        'UNIQUE (work_userid, work_id)',
        'wechat work user work_userid with work_id is existed！'
    )]

    @api.model
    def create(self, vals):
        if vals.get('avatar_url'):
            try:
                vals['image_1920'] = base64.encodebytes(
                    get_img_data(vals['avatar_url']))
            except:
                _logger.error('work_userid %s get img data error' %
                              vals['work_userid'])
        work_user = super(WorkUser, self).create(vals)
        return work_user

    def write(self, vals):
        if vals.get('avatar_url') and (
            vals.get('avatar_url') != self._origin.avatar_url or
            not self._origin.image_1920
        ):
            try:
                vals['image_1920'] = base64.encodebytes(
                    get_img_data(vals['avatar_url']))
            except:
                _logger.error('work_userid %s get img data error' %
                              vals['work_userid'])
        res = super(WorkUser, self).write(vals)
        return res

    def _parse_values(self, values):
        if 'userid' in values:
            values['work_userid'] = values['userid']
        if 'name' in values:
            values['livechat_username'] = values['name']
        if 'mobile' in values:
            if values['mobile'].strip() != '':
                values['mobile'] = phone_validation.phone_format(values['mobile'])
            else:
                values.pop('mobile')
        if 'email' in values:
            values['email'] = values['email'].strip()
            if values['email'] == '':
                values.pop('email')
        if 'telephone' in values and values['telephone'].strip() != '':
            values['phone'] = phone_validation.phone_format(values['telephone'])
        if 'gender' in values:
            if values['gender'] in ('1', 'male'):
                values['gender'] = 'male'
            elif values['gender'] in ('2', 'female'):
                values['gender'] = 'female'
            else:
                values['gender'] = 'other'
        if 'position' in values:
            values['function'] = values['position']
        if 'avatar' in values and values['avatar'] != None and values['avatar'].startswith('http'):
            values['avatar_url'] = values['avatar']

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def update_from_wechat_work(self, wechat_work, user_info):
        user_record = self.env['wechat.work.user']._parse_values(user_info)
        user_record.update({
            'work_id': wechat_work.id,
            'company_id': wechat_work.company_id.id,
            'parent_id': wechat_work.company_id.partner_id.id,
        })
        # user_record.pop('gender')

        work_user = self.search(
            [('work_userid', '=', user_record.get('work_userid')),
             ('work_id', '=', wechat_work.id)], limit=1)
        if work_user.exists():
            # 设置用户权限和公司的基本操作权限
            work_user.user_id.update_from_wechat_work(
                user_record)
            work_user.write(user_record)
        else:
            user = self.env['res.users'].search(
                ['|', ('login', '=', user_record.get('work_userid')),
                 '&', ('mobile', '!=', False), ('mobile', '=', user_record.get('mobile'))])
            if user.exists():
                user.update_from_wechat_work(
                    user_record)
                user_record.update({
                    'user_id': user.id
                })
            else:
                # user = self.env['res.users'].create_from_wechat_work(
                #    user_record)
                user_record.update({
                    'active': True,
                    'login': user_record.get('work_userid'),
                    'company_ids': [(4, user_record.get('company_id'))],
                    'notification_type': 'inbox',
                })
                if user_record.get('status') != 1:
                    user_record.update({
                        'groups_id': [self.env.ref('base.group_portal').id]
                    })

            work_user = self.create(user_record)

        # sync external user
        self.env['wechat.work.external.user'].sync(wechat_work, work_user)
        return work_user

    def _change_department(self, msg):
        return False

    def _change_contact_detail(self, msg, user_info):
        return False

    def change_contact(self, msg):
        corp_id = msg.target
        wechat_work, entry = self.env['wechat.work.config'].retrieve_entry(
            corp_id=corp_id)
        work_user = None
        if msg.change_type == 'delete_user':
            work_user = self.update_from_wechat_work(wechat_work, {
                'userid': msg.user_id,
                'status': 5,
                'enable': 0
            })
        elif msg.change_type in ['create_user', 'update_user']:
            user_info = entry.contacts_client.user.get(msg.user_id)
            work_user = self.update_from_wechat_work(wechat_work, user_info)
            work_user._change_contact_detail(msg, user_info)
        elif msg.change_type in ['create_party', 'update_party', 'delete_party']:
            self._change_department(msg)
        elif msg.change_type == 'update_tag':
            pass

        return work_user
