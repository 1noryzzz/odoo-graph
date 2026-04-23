# -*- coding: utf-8 -*-

import logging
import random

from cache_base import retrieve_cache_base
from odoo import _, models, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

CHPWD_SMS_CODE_PREFIX = 'ifs_gar_chpwd_sms_verification_code'
CHPWD_SMS_CODE_EXPIRES_IN = 3 * 60


class IfsGarChpwdSmsCode(models.TransientModel):
    _name = 'ifs.gar.chpwd.sms.code'
    _inherit = ['uuid.short.mixin']
    _description = '修改支付密码短信验证码'
    _order = 'create_date desc'

    _template_code = 'CHPWD_SMS_330465942'

    _sql_constraints = [
        ('mobile_uniq', 'unique (mobile)', _('手机号已存在'))
    ]

    mobile = fields.Char(string='手机号', required=True)
    verification_code = fields.Char(
        string='验证码', compute='_compute_verification_code')

    def _compute_verification_code(self):
        for record in self:
            vfcode = ''
            cache_base = retrieve_cache_base(self.env, 'TOKEN-CACHE')
            with cache_base.redis_db.connection_open() as db:
                vfcode = db.get(
                    f'{CHPWD_SMS_CODE_PREFIX}_txx_{record.mobile}')
            record.verification_code = vfcode if vfcode else False

    def generate_verification_code(self, mobile):
        chars = '0123456789'
        verification_code = ''.join(
            random.SystemRandom().choice(chars) for _ in range(6))
        cache_base = retrieve_cache_base(request.env, 'TOKEN-CACHE')
        with cache_base.redis_db.connection_open() as db:
            db.setex(
                name=f'{CHPWD_SMS_CODE_PREFIX}_txx_{mobile}',
                value=verification_code, time=CHPWD_SMS_CODE_EXPIRES_IN)
        return verification_code

    def check_verification_code(self, mobile, verification_code):
        verify = False
        cache_base = retrieve_cache_base(self.env, 'TOKEN-CACHE')
        with cache_base.redis_db.connection_open() as db:
            vfcode = db.get(f'{CHPWD_SMS_CODE_PREFIX}_txx_{mobile}')
            if vfcode and vfcode.decode('utf-8') == verification_code:
                db.getdel(f'{CHPWD_SMS_CODE_PREFIX}_txx_{mobile}')
                verify = True
        return verify

    def send_verification_code(self, phone, raise_exception=False):
        template = self.env['sms.template'].search(
            [('code', '=', self._template_code)])
        if template:
            params = template._render_field(
                'template_param', [self.id], compute_lang=True)[self.id]
            aliyun_data = [{
                'res_id': self.id,
                'number': phone,
                'content': params,
                'code': template.aliyun_code,
                'sign_name': template.sign_name
            }]

            try:
                aliyun_result = self.env['galaxy.aliyun.sms.api']._send_sms_batch(
                    aliyun_data)
            except Exception as e:
                _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(
                    self.ids), self.ids, e)
                if raise_exception:
                    raise
            else:
                _logger.info('Send batch %s SMS: %s: gave %s',
                             len(self.ids), self.ids, aliyun_result)
