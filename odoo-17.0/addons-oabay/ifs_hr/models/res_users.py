# -*- coding: utf-8 -*-
import logging

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def signup_from_inclusive_financing(self, vals):
        exist_user = self.with_context(active_test=False).sudo().search(
            [('login', '=', vals.get('mobile_phone'))])
        if exist_user.exists():
            raise ValidationError(_('手机号已存在！'))

        # return self.with_context(mail_notrack=True).sudo().create({
        return self.with_context(signup_valid=True, no_reset_password=True).sudo().create({
            'active': True,
            # vals.get('mobile_phone', vals.get('work_email')),
            'login': vals.get('login'),
            'email': vals.get('work_email', f'{vals.get("mobile_phone")}@139.com'),
            'phone': vals.get('mobile_phone'),
            'name': vals.get('name'),
            'company_id': vals.get('company_id'),
            'company_ids': [fields.Command.set([vals.get('company_id')])],
            # 'parent_id': employee.company_id.partner_id.id,
            'partner_id': vals.get('user_partner_id', False),
            'user_id': self.env.context.get('sales_user_id', False),
            'action_id': self.env.context.get('ifs_default_action_id', False),
            'notification_type': 'inbox',
            # 'groups_id': [fields.Command.set(employee.work_position_ids.groups_id.ids)],
            'password': vals.get('mobile_phone')[-6:],
            'default_pwd': vals.get('mobile_phone')[-6:]
        })

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        uid = super(ResUsers, cls).authenticate(
            db, login, password, user_agent_env)
        if user_agent_env and 'ot_password' in user_agent_env:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                otp = env['hr.employee'].is_need_one_time_passwd(uid)
                if otp:
                    try:
                        otp.check_passwd(user_agent_env.get('ot_password'))
                    except Exception:
                        if user_agent_env.get('ot_password') != \
                                env['ir.config_parameter'].sudo().get_param('ifs.hr.otp.universal.password', False):
                            _logger.info(
                                "Login failed for db:%s login:%s cause by one time password invalid", db, login)
                            raise

        return uid
