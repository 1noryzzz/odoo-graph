# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('send_reset_mail', False):
            if self.env.context.get('invite', False):
                # 发送邀请
                self.mapped('partner_id').signup_prepare(
                    signup_type="reset", expiration=datetime.now() + timedelta(minutes=3))

                template = False
                if self.env.context.get('invite') == 'supplier':
                    template = self.env.ref(
                        'ifs_gar_invite.invite_supplier_mail', raise_if_not_found=False)
                else:
                    template = self.env.ref(
                        'ifs_gar_invite.invite_merchant_mail', raise_if_not_found=False)
                assert template._name == 'mail.template'

                email_values = {
                    'email_cc': False,
                    'auto_delete': True,
                    'recipient_ids': [],
                    'partner_ids': [],
                    'scheduled_date': False,
                }

                for user in self:
                    if not user.email:
                        raise UserError(_("邀约邮件发送失败！%s 没有邮箱地址。", self.name))
                    email_values['email_to'] = user.email

                    with self.env.cr.savepoint():
                        force_send = not(
                            self.env.context.get('import_file', False))
                        is_send_sms = self.env['ir.config_parameter'].sudo().get_param('galaxy.aliyun.send.sms')
                        if is_send_sms:
                            sms_template_id = self.env['sms.template'].search([('code','=','SMS_246985088')])
                            self.env['sms.sms'].create({
                                'partner_id':self.partner_id.id,
                                'template_id':sms_template_id.id
                            }).send()
                        template.send_mail(
                            user.id, force_send=force_send, raise_exception=True, email_values=email_values)
                    _logger.info(
                        "Password reset email sent for user <%s> to <%s>", user.login, user.email)
            else:
                super(ResUsers, self).action_reset_password()
