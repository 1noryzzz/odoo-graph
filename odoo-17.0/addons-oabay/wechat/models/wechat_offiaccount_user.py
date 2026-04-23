# -*- coding: utf-8 -*-

import base64
from string import digits
import geohash
import logging
import requests

from datetime import datetime
from urllib.parse import urlparse
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from wechatpy.exceptions import WeChatClientException

from ..rpc import wechat_entry

_logger = logging.getLogger(__name__)


def get_img_data(pic_url):
    headers = {
        'Accept': 'textml,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
        'Cache-Control': 'no-cache',
        # 'Host': 'mmbiz.qpic.cn',
        'Host': urlparse(pic_url).netloc,
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    }
    r = requests.get(pic_url, headers=headers, timeout=50)
    return r.content


def _default_offiaccount_id(self):
    return self.env.context.get(
        'offiaccount_id', False) or self.env.context.get('active_id', False)


class OffiaccountUser(models.Model):

    _name = 'wechat.offiaccount.user'
    _description = 'Offiaccount Users'
    _inherit = ['wechat.user.mixin']
    _order = 'subscribe_time desc'

    offiaccount_id = fields.Many2one(
        'wechat.offiaccount.config', required=True, string='Wechat Offiaccount', ondelete='cascade')
    tag_ids = fields.Many2many('wechat.offiaccount.taglist', string='TagLists',
                               column1='partner_id', column2='tag_id')
    group_id = fields.Selection('_get_groups', string='Group', default='0')

    subscribe = fields.Boolean('Subscribed', )
    # fields.Char('Subscribe Time', )
    subscribe_time = fields.Datetime(string='Subscribe Time')
    subscribe_scene = fields.Char('Subscribe Scene', )
    remark = fields.Char('Remark', )

    longitude = fields.Float(
        string='经度', digits=(16, 7), default=0.0)
    latitude = fields.Float(
        string='纬度', digits=(16, 7), default=0.0)
    precision = fields.Float(
        string='地理位置精度', digits=(16, 7), default=9999.0
    )
    geohash_code = fields.Char(
        string='经纬度编码', store=True, compute='_compute_geohash')

    qr_scene = fields.Char('qr_scene', )
    qr_scene_str = fields.Char('qr_scene_str', )

    _sql_constraints = [(
        'offiaccount_user_open_id_unique',
        'UNIQUE (offiaccount_id, open_id)',
        'Offiaccount user open_id with offiaccount_id is existed！'
    )]

    @api.depends('longitude', 'latitude')
    def _compute_geohash(self):
        for res in self:
            res.geohash_code = geohash.encode(
                res.latitude, res.longitude)

    @api.model
    def _get_groups(self):
        # return [('0', '默认组')]
        groups = self.env['wechat.offiaccount.group'].search([])
        return [(str(group.offiaccount_group_id), group.name) for group in groups] or [('0', '默认组')]

    @api.model
    def create(self, vals):
        if vals.get('avatar_url'):
            try:
                vals['image_1920'] = base64.encodebytes(
                    get_img_data(vals['avatar_url']))
            except:
                _logger.error('wechat user %s get img data error' %
                              vals['open_id'])
        return super(OffiaccountUser, self).create(vals)

    def write(self, vals):
        if vals.get('avatar_url') and (
            vals.get('avatar_url') != self._origin.avatar_url or
            not self._origin.image_1920
        ):
            try:
                vals['image_1920'] = base64.encodebytes(
                    get_img_data(vals['avatar_url']))
            except:
                _logger.error('wechat user %s get img data error' %
                              vals['open_id'])
        return super(OffiaccountUser, self).write(vals)

    def _parse_values(self, values, tagid_tag_list):
        if 'openid' in values:
            values['open_id'] = values['openid']
        if 'unionid' in values:
            values['union_id'] = values['unionid']
        if 'language' in values:
            values['lang'] = 'zh_CN'  # values['language']
            values['tz'] = 'Asia/Shanghai'
        if 'sex' in values:
            if values['sex'] == 1:
                values['gender'] = 'male'
            elif values['sex'] == 2:
                values['gender'] = 'female'
            else:
                values['gender'] = 'other'
        if 'groupid' in values:
            values['group_id'] = str(values['groupid'])
        if 'tagid_list' in values:
            values['tag_ids'] = [tagid_tag_list.get(
                tagid) for tagid in values['tagid_list']]
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
        if 'subscribe_time' in values:
            values['subscribe_time'] = datetime.fromtimestamp(
                values['subscribe_time'])
        if 'headimgurl' in values and values['headimgurl'].startswith('http'):
            values['avatar_url'] = values['headimgurl']
        values['type'] = 'contact'

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def tag_user(self, tag):
        self.ensure_one()

        offiaccount, entry = self.env[
            'wechat.offiaccount.config'].retrieve_entry(
            app_id=self.offiaccount_id.app_id)
        if not entry.app_id:
            raise ValidationError(_('Wechat Offiaccount Uninitialized'))

        entry.client.tag.tag_user(
            tag_id=tag.offiaccount_tag_id, user_id=self.open_id)

    def signup(self, offiaccount, user_info, tagid_tag_list=False, user_id=False):
        if not tagid_tag_list:
            tags = self.env['wechat.offiaccount.taglist'].search(
                [('offiaccount_id.id', '=', offiaccount.id)])
            tagid_tag_list = {}
            for tag in tags:
                tagid_tag_list[tag.offiaccount_tag_id] = tag.id

        info = self._parse_values(user_info, tagid_tag_list)

        offiaccount_user = self.search(
            ['&', ('open_id', '=', info.get('open_id')),
             ('offiaccount_id.id', '=', offiaccount.id)], limit=1)
        if user_id:
            # 如果传入确定的 user_id，则当前是做用户绑定的操作
            # 此时删掉已存在的公众号用户记录，并把信息绑定到已存在的用户上
            user = self.env['res.users'].browse(user_id)
            if user.exists():
                if offiaccount_user.exists():
                    old_partner_id = offiaccount_user.partner_id.id
                    info.update({
                        'partner_id': user.partner_id.id,
                        'offiaccount_id': offiaccount.id
                    })
                    offiaccount_user.write(info)
                    self.env['res.partner'].browse(old_partner_id).unlink()
                else:
                    info['partner_id'] = user.partner_id.id
                    info['offiaccount_id'] = offiaccount.id
                    self.create(info)
        elif not offiaccount_user.exists():
            partner = self.env['res.partner'].search(
                [('union_id', '=', True), ('union_id', '=', info.get('union_id'))], limit=1)
            if partner.exists():
                info['partner_id'] = partner.id
            else:
                info['name'] = '公众号[%s]用户[%s]' % (
                    offiaccount.name, self.env['ir.sequence'].next_by_code('wechat.offiaccount.user.name'))
                # info['company_ids'] = [fields.Command.set([offiaccount.website_id.company_id.id])]

            info['offiaccount_id'] = offiaccount.id

            # try:
            self.create(info)
            # except:
            #     info.pop('image_1920')
            #     info.pop('avatar_url')
            #     self.create(info)
        else:
            # try:
            offiaccount_user.write(info)
            # except:
            #     info.pop('image_1920')
            #     offiaccount_user.write(info)

    @api.model_callback
    def _process_message(self, entry, message, callback_action, callback_log):
        # openid = message.source

        # offiaccount = self.env['wechat.offiaccount.config'].search(
        #     [('app_id', '=', entry.app_id)])
        #TODO: process

        return message.content

    @api.model_callback
    def _process_event_subscribe(self, entry, message, callback_action, callback_log):
        # serviceid = message.target
        openid = message.source

        user_info = entry.client.user.get(openid)
        offiaccount = self.env['wechat.offiaccount.config'].search(
            [('app_id', '=', entry.app_id)])

        if message.event == 'subscribe':
            self.env['wechat.offiaccount.group'].with_context(
                offiaccount_id=offiaccount.id).wechat_sync()
            self.env['wechat.offiaccount.taglist'].with_context(
                offiaccount_id=offiaccount.id).wechat_sync()
            self.env.cr.commit()

        tags = self.env['wechat.offiaccount.taglist'].search(
            [('offiaccount_id.id', '=', offiaccount.id)])
        tagid_tag_list = {}
        for tag in tags:
            tagid_tag_list[tag.offiaccount_tag_id] = tag.id
        try:
            self.signup(offiaccount, user_info, tagid_tag_list)
            _logger.info('sync openid = %s, union_id=%s' %
                         (openid, user_info.get('union_id')))
        except:
            _logger.error('sync openid = %s, union_id=%s' %
                          (openid, user_info.get('union_id')))

        if message.event == 'subscribe':
            return '您终于来了！欢迎关注'

        return ''

    @api.model_callback
    def _process_event_location(self, entry, message, callback_action, callback_log):
        openid = message.source

        offiaccount = self.env['wechat.offiaccount.config'].search(
            [('app_id', '=', entry.app_id)])
        offiaccount_user = self.search(
            ['&', ('open_id', '=', openid),
             ('offiaccount_id.id', '=', offiaccount.id)], limit=1)

        if message.event == 'location':
            # TODO: 在 precision 表示的精度不够时，丢弃这个定位
            offiaccount_user.write({
                'longitude': message.longitude,
                'latitude': message.latitude,
                'precision': message.precision,
            })

        return 'success'

    def generate_temp_qr_code(self, scene_str, expire_seconds=180):
        '''
        生成临时二维码
        此方法需要以单条记录来调用，为此用户生成一个二维码
        '''
        self.ensure_one()

        _, entry = self.env[
            'wechat.offiaccount.config'].retrieve_entry(
            app_id=self.offiaccount_id.app_id)
        if not entry.app_id:
            raise ValidationError(_('微信公众号配置错误！'))

        return entry.client.qrcode.create({
            "expire_seconds": expire_seconds,
            "action_name": "QR_STR_SCENE",
            "action_info": {"scene": {"scene_str": scene_str}},
        })

    @api.model
    def wechat_sync(self, start_index=0):
        sync_max_line = 50

        if start_index == 0:
            self.env['wechat.offiaccount.group'].wechat_sync()
            self.env['wechat.offiaccount.taglist'].wechat_sync()
            self.env.cr.commit()

        offiaccount_id = self.env.context.get(
            'offiaccount_id', 0) or self.env.context.get('active_id', 0)
        offiaccount = self.env['wechat.offiaccount.config'].browse(
            offiaccount_id)
        if not offiaccount.exists():
            raise ValidationError(_('Wechat Offiaccount Uninitialized'))

        entry = wechat_entry.retrieve_wechat_entry(
            self.env, offiaccount.app_id)
        if not entry.app_id:
            raise ValidationError(_('Wechat Offiaccount Uninitialized'))

        tags = self.env['wechat.offiaccount.taglist'].search(
            [('offiaccount_id.id', '=', offiaccount.id)])
        tagid_tag_list = {}
        for tag in tags:
            tagid_tag_list[tag.offiaccount_tag_id] = tag.id

        current_line_index = 0
        has_next = False
        try:
            for openid in entry.client.user.iter_followers():
                if current_line_index < start_index or (
                        current_line_index - start_index == sync_max_line):
                    current_line_index += 1
                    continue

                if current_line_index - start_index > sync_max_line:
                    current_line_index -= 1
                    has_next = True
                    break

                user_info = entry.client.user.get(openid)
                try:
                    self.signup(offiaccount, user_info, tagid_tag_list)
                    self.env.cr.commit()
                    _logger.info('sync line index is %d, union_id=%s' %
                                 (current_line_index, user_info.get('union_id')))
                except:
                    _logger.error('sync line index is %d, union_id=%s' %
                                  (current_line_index, user_info.get('union_id')))
                current_line_index += 1
        except WeChatClientException as e:
            raise ValidationError(_('Wechat server error: %s') % e)

        return {
            'type': 'warning' if has_next else 'success',
            'action': has_next and 'continue',
            'title': _('Success'),
            'synced_line': (current_line_index - start_index),
            'message': 'Synchronized %d users' % current_line_index,
            'sticky': False,
        }


class TagList(models.Model):
    _name = 'wechat.offiaccount.taglist'
    _order = 'offiaccount_tag_id'
    _description = '微信公众号内的用户标签'

    offiaccount_id = fields.Many2one(
        'wechat.offiaccount.config', required=True, string='公众号',
        ondelete='cascade', default=lambda self: _default_offiaccount_id(self))
    offiaccount_tag_id = fields.Integer('标签ID')
    name = fields.Char('标签名', required=True)
    count = fields.Integer('用户数', default=0)

    @api.model
    def create(self, vals):
        if 'is_from_wechat' not in vals:
            offiaccount = self.env['wechat.offiaccount.config'].browse(
                vals.get('offiaccount_id'))
            if offiaccount.exists():
                entry = wechat_entry.retrieve_wechat_entry(
                    self.env, offiaccount.app_id)
                if not entry.app_id:
                    raise ValidationError(
                        _('Wechat Offiaccount Uninitialized'))

                try:
                    new_tag = entry.client.tag.create(vals.get('name'))
                    vals.update({
                        'offiaccount_tag_id': new_tag.get('id')
                    })
                except WeChatClientException as e:
                    tags = entry.client.tag.get()
                    for tag in tags:
                        if tag.get('name') == vals.get('name'):
                            vals['offiaccount_tag_id'] = tag.get('id')
            else:
                raise ValidationError(_('Wechat Offiaccount Uninitialized'))
        else:
            vals.pop('is_from_wechat')
        return super(TagList, self).create(vals)

    def write(self, vals):
        if 'is_from_wechat' not in vals:
            entry = wechat_entry.retrieve_wechat_entry(
                self.env, self.offiaccount_id.app_id)
            if not entry.app_id:
                raise ValidationError(_('Wechat Offiaccount Uninitialized'))

            msg = entry.client.tag.update(
                self.offiaccount_tag_id, vals.get('name'))
            if msg.get('errcode') != 0:
                raise ValidationError(_('Wechat Server Error (%d): %s') % (
                    msg.get('errcode'), msg.get('errmsg')))
        else:
            vals.pop('is_from_wechat')

        return super(TagList, self).write(vals)

    def unlink(self):
        entry = wechat_entry.retrieve_wechat_entry(
            self.env, self.offiaccount_id.app_id)
        if not entry.app_id:
            raise ValidationError(_('Wechat Offiaccount Uninitialized'))

        for tag in self:
            msg = entry.client.tag.delete(tag.offiaccount_tag_id)
            if msg.get('errcode') != 0:
                raise ValidationError(_('Wechat Server Error (%d): %s') % (
                    msg.get('errcode'), msg.get('errmsg')))

        return super(TagList, self).unlink()

    @api.model
    def wechat_sync(self, start_index=0):
        offiaccount_id = self.env.context.get(
            'offiaccount_id', 0) or self.env.context.get('active_id', 0)
        offiaccount = self.env['wechat.offiaccount.config'].browse(
            offiaccount_id)
        if offiaccount.exists():
            entry = wechat_entry.retrieve_wechat_entry(
                self.env, offiaccount.app_id)
            if not entry.app_id:
                raise ValidationError(_('Wechat Offiaccount Uninitialized'))

            try:
                tags = entry.client.tag.get()
            except WeChatClientException as e:
                raise ValidationError(_('Wechat server error: %s') % e)

            _logger.info('tags = %s' % tags)
            for tag in tags:
                rs = self.search(
                    ['&', ('offiaccount_tag_id', '=', tag['id']), ('offiaccount_id', '=', offiaccount_id)])
                if rs.exists():
                    rs.write({
                        'name': tag['name'],
                        'count': tag['count'],
                        'is_from_wechat': True,
                    })
                else:
                    self.create({
                        'offiaccount_id': offiaccount_id,
                        'offiaccount_tag_id': tag['id'],
                        'name': tag['name'],
                        'count': tag['count'],
                        'is_from_wechat': True,
                    })
            return {
                'type': 'success',
                'title': _('Success'),
                'message': _('Taglist synced with wechat.'),
                'sticky': False,
            }

        raise ValidationError(_('Wechat Offiaccount Uninitialized'))


class OffiaccountGroup(models.Model):
    _name = 'wechat.offiaccount.group'
    _order = 'offiaccount_group_id'
    _description = 'Wechat Offiaccount Group'

    offiaccount_id = fields.Many2one(
        'wechat.offiaccount.config', required=True, string='Wechat Offiaccount',
        ondelete='cascade', default=lambda self: _default_offiaccount_id(self))
    offiaccount_group_id = fields.Integer('Group Id', )
    name = fields.Char('Group Name')
    count = fields.Integer('Group User Count', default=0)

    @api.model
    def create(self, vals):
        if 'is_from_wechat' not in vals:
            raise ValidationError(_("Group can't be operate anymore!"))

        vals.pop('is_from_wechat')
        return super(OffiaccountGroup, self).create(vals)

    def write(self, vals):
        if 'is_from_wechat' not in vals:
            raise ValidationError(_("Group can't be operate anymore!"))

        vals.pop('is_from_wechat')
        return super(OffiaccountGroup, self).write(vals)

    def unlink(self):
        raise ValidationError(_("Group can't be operate anymore!"))

    @api.model
    def wechat_sync(self, start_index=0):
        offiaccount_id = self.env.context.get(
            'offiaccount_id', 0) or self.env.context.get('active_id', 0)
        offiaccount = self.env['wechat.offiaccount.config'].browse(
            offiaccount_id)
        if offiaccount.exists():
            entry = wechat_entry.retrieve_wechat_entry(
                self.env, offiaccount.app_id)
            if not entry.app_id:
                raise ValidationError(_('Wechat Offiaccount Uninitialized'))

            try:
                groups = entry.client.group.get()
            except WeChatClientException as e:
                raise ValidationError(_('Wechat server error: %s') % e)

            _logger.info('groups = %s' % groups)
            for group in groups:
                rs = self.search(
                    ['&', ('offiaccount_group_id', '=', group['id']), ('offiaccount_id', '=', offiaccount_id)])
                if rs.exists():
                    rs.write({
                        'name': group['name'],
                        'count': group['count'],
                        'is_from_wechat': True,
                    })
                else:
                    self.create({
                        'offiaccount_id': offiaccount_id,
                        'offiaccount_group_id': group['id'],
                        'name': group['name'],
                        'count': group['count'],
                        'is_from_wechat': True,
                    })
            return {
                'type': 'success',
                'title': _('Success'),
                'message': _('Group synced with wechat.'),
                'sticky': False,
            }

        raise ValidationError(_('Wechat Offiaccount Uninitialized'))
