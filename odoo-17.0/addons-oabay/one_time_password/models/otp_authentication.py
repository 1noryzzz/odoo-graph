# -*- coding: utf-8 -*-

import ctypes
import logging
import os
import sys
import time

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError

_logger = logging.getLogger(__name__)

OTP_RESULT = {
    'OTP_SUCCESS': 0,  # 操作成功
    'OTP_ERR_INVALID_PARAMETER': 1,  # 参数无效
    'OTP_ERR_CHECK_PWD': 2,  # 认证失败
    'OTP_ERR_SYN_PWD': 3,  # 同步失败
    'OTP_ERR_REPLAY': 4,  # 动态口令被重放
}

OTP_LIB = {
    'z201': 'libetotpverify.so'
}


class OTPAuthentication(models.Model):
    _name = 'otp.authentication'
    _description = '动态令牌的基础数据表'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc, device_id desc'
    _rec_name = 'device_id'

    _sql_constraints = [
        ('device_id_uniq', 'unique(device_id)',
         '设备编号已存在')
    ]

    device_id = fields.Char(
        '设备编号', index=True, required=True, tracking=True)
    auth_key = fields.Char('令牌密钥', required=True, tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', '未启用'),
        ('normal', '正常'),
        ('paused', '已停用')
    ], string='设备状态', default='draft', tracking=True)
    cycles = fields.Integer('变化周期', default=60)
    syncwnd = fields.Integer('同步窗口', default=20, tracking=True)
    drift = fields.Integer('漂移值', default=0)
    result = fields.Integer('成功调用后的返回值', default=0)
    log_ids = fields.One2many(
        'otp.authentication.log', 'otp_auth_id', string='使用记录')
    company_id = fields.Many2one('res.company', string='公司', index=True, tracking=True)

    def _get_full_path(self, file_name):
        paths = sys.path
        for path in paths:
            try:
                if file_name in os.listdir(path):
                    return '/'.join([path, file_name])
            except (FileExistsError, FileNotFoundError) as e:
                _logger.error(e)

    def action_approval(self):
        self.ensure_one()
        self.state = 'normal'

    def action_pause(self):
        self.ensure_one()
        self.state = 'paused'

    def action_check_pwd(self):
        new_context = (dict(self._context) or {})
        new_context.update({
            'default_otp_auth_id': self.id,
        })

        return {
            'name': _('认证'),
            'type': 'ir.actions.act_window',
            'res_model': 'otp.check',
            'res_id': None,
            'view_mode': 'form',
            'view_type': 'form',
            'context': new_context,
            'view_id': self.env.ref('one_time_password.otp_check_view_form').id,
            'target': 'new',
            'flags': {'initial_mode': 'edit'},
        }

    def action_sync(self):
        new_context = (dict(self._context) or {})
        new_context.update({
            'default_otp_auth_id': self.id,
        })

        return {
            'name': _('同步'),
            'type': 'ir.actions.act_window',
            'res_model': 'otp.sync',
            'res_id': None,
            'view_mode': 'form',
            'view_type': 'form',
            'context': new_context,
            'view_id': self.env.ref('one_time_password.otp_sync_view_form').id,
            'target': 'new',
            'flags': {'initial_mode': 'edit'},
        }

    def check_passwd(self, passwd):
        curr_drift = ctypes.c_int(0)
        curr_result = ctypes.c_int(0)

        if self.state != 'normal':
            raise UserError(_('设备未启用！'))

        if type(OTP_LIB.get('z201')) == str:
            OTP_LIB.update({
                'z201': ctypes.CDLL(self._get_full_path(OTP_LIB.get('z201')))
            })
        rst = OTP_LIB.get('z201').ET_CheckPwdz201(
            ctypes.c_char_p(bytes(self.auth_key, encoding='utf-8')),
            ctypes.c_int(int(time.time())),
            ctypes.c_int(0),
            ctypes.c_int(self.cycles),
            ctypes.c_int(self.drift),
            ctypes.c_int(self.syncwnd),
            ctypes.c_int(self.result),
            ctypes.c_char_p(bytes(passwd, encoding='utf-8')),
            ctypes.c_int(len(passwd)),
            ctypes.byref(curr_result),
            ctypes.byref(curr_drift))

        self.env['otp.authentication.log'].create({
            'otp_auth_id': self.id,
            'drift': curr_drift.value,
            'result': curr_result.value,
            'auth_result': str(rst)
        })
        self.env.cr.commit()

        if rst == OTP_RESULT.get('OTP_ERR_REPLAY'):
            _logger.warning(_('动态口令被重放！'))

        if rst == OTP_RESULT.get('OTP_ERR_INVALID_PARAMETER'):
            raise UserError(_('调用动态令牌的参数无效！'))
        elif rst != OTP_RESULT.get('OTP_SUCCESS'):
            raise AccessDenied(_('动态令牌认证失败！'))

        self.write({
            'drift': curr_drift.value,
            'result': curr_result.value
        })

    def sync(self, passwd1, passwd2):
        curr_drift = ctypes.c_int(0)
        curr_result = ctypes.c_int(0)

        if type(OTP_LIB.get('z201')) == str:
            OTP_LIB.update({
                'z201': ctypes.CDLL(self._get_full_path(OTP_LIB.get('z201')))
            })
        rst = OTP_LIB.get('z201').ET_Syncz201(
            ctypes.c_char_p(bytes(self.auth_key, encoding='utf-8')),
            ctypes.c_int(int(time.time())),
            ctypes.c_int(0),
            ctypes.c_int(self.cycles),
            ctypes.c_int(self.drift),
            ctypes.c_int(self.syncwnd),
            ctypes.c_int(self.result),
            ctypes.c_char_p(bytes(passwd1, encoding='utf-8')),
            ctypes.c_int(len(passwd1)),
            ctypes.c_char_p(bytes(passwd2, encoding='utf-8')),
            ctypes.c_int(len(passwd2)),
            ctypes.byref(curr_result),
            ctypes.byref(curr_drift))

        if rst == OTP_RESULT.get('OTP_ERR_INVALID_PARAMETER'):
            raise UserError(_('调用动态令牌的参数无效！'))
        elif rst == OTP_RESULT.get('OTP_ERR_CHECK_PWD'):
            raise AccessDenied(_('动态令牌认证失败！'))
        elif rst == OTP_RESULT.get('OTP_ERR_SYN_PWD'):
            raise AccessDenied(_('动态令牌同步失败！'))
        elif rst == OTP_RESULT.get('OTP_ERR_REPLAY'):
            raise AccessDenied(_('动态口令被重放！'))

        self.write({
            'drift': curr_drift.value,
            'result': curr_result.value
        })


class OTPAuthenticationLog(models.Model):
    _name = 'otp.authentication.log'
    _description = '动态令牌校验日志'
    _order = 'write_date desc'

    otp_auth_id = fields.Many2one(
        'otp.authentication', required=True, ondelete='restrict', string='动态令牌')
    code = fields.Char('流水号', required=True)
    drift = fields.Integer('漂移值', default=0)
    result = fields.Integer('成功调用后的返回值', default=0)
    auth_result = fields.Selection([
        (str(OTP_RESULT.get('OTP_SUCCESS')), '操作成功'),
        (str(OTP_RESULT.get('OTP_ERR_INVALID_PARAMETER')), '参数无效'),
        (str(OTP_RESULT.get('OTP_ERR_CHECK_PWD')), '认证失败'),
        (str(OTP_RESULT.get('OTP_ERR_SYN_PWD')), '同步失败'),
        (str(OTP_RESULT.get('OTP_ERR_REPLAY')), '动态口令被重放'),
    ], string='操作结果')

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'otp.authentication.log') or _('New')

        return super(OTPAuthenticationLog, self).create(vals)
