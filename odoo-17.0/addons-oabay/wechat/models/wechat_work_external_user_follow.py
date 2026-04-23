# -*- coding: utf-8 -*-

import base64
import json
import logging
from datetime import datetime

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkExternalUserFollow(models.Model):

    _name = 'wechat.work.external.user.follow'
    _description = 'External User Follow'
    _order = 'id desc'

    work_user_id = fields.Many2one(
        'wechat.work.user', required=True, string='Wechat Work User', ondelete='cascade')
    external_user_id = fields.Many2one(
        'wechat.work.external.user', required=True, string='Wechat Work External User', ondelete='cascade')
    work_userid = fields.Char('Wechat Work UserId', required=True)
    remark = fields.Char('Follow Remark')
    description = fields.Char('Follow Description')
    subscribe_time = fields.Datetime(string='Subscribe Time')
    tags = fields.Char('Tags')
    remark_corp_name = fields.Char('Remark Corpration Name')
    remark_mobiles = fields.Char('Remark Mobiles')
    add_way = fields.Integer('Add way')
    oper_userid = fields.Char('Operate UserId')
    state = fields.Char('State')

    _sql_constraints = [(
        'work_external_user_follow_unique',
        'UNIQUE (work_user_id, external_user_id)',
        'Work external user follow relationship exist！'
    )]

    def _parse_values(self, values):
        if 'userid' in values:
            values['work_userid'] = values['userid']
        if 'createtime' in values:
            values['subscribe_time'] = datetime.fromtimestamp(
                values['createtime'])
        if 'tags' in values:
            values['tags'] = json.dumps(values['tags'])
        if 'remark_mobiles' in values:
            values['remark_mobiles'] = json.dumps(values['remark_mobiles'])

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals
    
    def update_from_wework(self, work_user, external_user_id, follow_infos):
        for follow_info in follow_infos:
            if work_user.work_userid == follow_info.get('userid'):
                info = self._parse_values(follow_info)
                external_user_follow = self.search(
                        ['&', ('work_user_id', '=', work_user.id),
                        ('external_user_id', '=', external_user_id)], limit=1)
                if not external_user_follow.exists():
                    info.update({
                        'work_user_id': work_user.id,
                        'external_user_id': external_user_id
                    })
                    self.create(info)
                else:
                    external_user_follow.write(info)
