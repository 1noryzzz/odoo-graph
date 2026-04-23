# -*- coding: utf-8 -*-
import logging

from odoo import _, api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecInviteLawRootUserWizard(models.TransientModel):
    _name = 'ifs.gar.invite.lawfirm.root.user.wizard'
    _inherit = 'ifs.base.company.root.user.wizard'
    _description = '创建受邀律师事务所根用户'

    def action_confirm(self):
        super().action_confirm()
        for user in self:
            if not user.work_email:
                raise UserError(_("邀约邮件发送失败！%s 没有邮箱地址。", self.name))
            config = self.env['ir.config_parameter'].sudo()
            is_send_sms = config.get_param('galaxy.aliyun.send.sms')
            invite_lawfirm = self.env['ifs.gar.invite.lawfirm'].search([('ifs_company_id', '=', self.ifs_company_id.id), (
                'factor_id.company_id', '=', self.env.company.id)])
            if is_send_sms:
                sms_template_id = self.env['sms.template'].search(
                    [('code', '=', 'INVITE_SMS_246985088')])
                self.env['sms.sms'].create({
                    'partner_id': invite_lawfirm.legal_id.id,
                    'template_id': sms_template_id.id
                }).send()
            email_values = {
                'email_cc': False,
                'auto_delete': True,
                'recipient_ids': [],
                'partner_ids': [],
                'scheduled_date': False,
            }
            is_send_mail = config.get_param('ifs_gar_invite.is_send_mail')
            email_default_receiver = config.get_param(
                'ifs_gar_invite.email_default_receiver')
            if email_default_receiver and not is_send_mail:
                email_values['email_to'] = email_default_receiver
            else:
                email_values['email_to'] = user.work_email
            template = self.env.ref(
                'ifs_gar_invite.invite_lawfirm_mail', raise_if_not_found=False)
            assert template._name == 'mail.template'
            with self.env.cr.savepoint():
                force_send = not (
                    self.env.context.get('import_file', False))
                template.send_mail(
                    invite_lawfirm.id, force_send=force_send, raise_exception=True, email_values=email_values)
                if invite_lawfirm.state == 'draft':
                    invite_lawfirm.state = 'sended'
                    invite_lawfirm.invite_date = fields.Datetime.now()
            _logger.info(
                "Invite email sent for user <%s> to <%s>", user.login, email_values['email_to'])
