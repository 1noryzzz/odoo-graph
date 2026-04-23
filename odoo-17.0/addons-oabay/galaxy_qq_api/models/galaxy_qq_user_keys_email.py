# -*- coding: utf-8 -*-

from odoo import _, models


VERIFICATION_CODE_EXPIRES_IN_EMAIL = 10 * 60


class GalaxyQqUserKeysEmail(models.Model):
    _inherit = "galaxy.qq.user.keys"

    def send_verification_email(self, email, email_from=False):
        if not email_from:
            alias_domain = (
                self.env["mail.alias.domain"]
                .sudo()
                .search([("default_from", "=", "service")], limit=1)
            )
            if alias_domain.exists():
                email_from = f"云腾智慧<{alias_domain.default_from}@{alias_domain.name}>"
            else:
                email_from = "云腾智慧"
        email_values = {
            "email_cc": False,
            "auto_delete": True,
            "recipient_ids": [],
            "partner_ids": [],
            "scheduled_date": False,
            "email_from": email_from,
            "email_to": email,
        }

        template = self.env.ref(
            "galaxy_qq_api.qq_user_login_mail", raise_if_not_found=False
        )
        if self.qq_user_id.app_id.user_id.id == self.qq_user_id.user_id.id:
            template = self.env.ref(
                "galaxy_qq_api.qq_user_signin_mail", raise_if_not_found=False
            )

        assert template._name == "mail.template"
        verification_code = self.qq_user_id.generate_verification_code(
            email, expires_in=VERIFICATION_CODE_EXPIRES_IN_EMAIL
        )
        with self.env.cr.savepoint():
            force_send = not (self.env.context.get("import_file", False))
            template.with_context(lang=self.env.lang).send_mail(
                self.id,
                force_send=force_send,
                raise_exception=True,
                email_values=email_values,
            )
            self.env["bus.bus"]._sendone(
                self,
                "email_verification",
                {
                    "access_token": self.access_token,
                    "event": "email_sended",
                },
            )

        return verification_code

    def get_verification_url(self):
        return f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/qqapi/email_verification?code={self.verification_code}&email={self.login_with}&platform_os={self.platform_os}&k={self.access_token}"
