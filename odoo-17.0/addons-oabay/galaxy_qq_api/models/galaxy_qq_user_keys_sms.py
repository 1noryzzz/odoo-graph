# -*- coding: utf-8 -*-

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class GalaxyQqUserKeysSMS(models.Model):
    _inherit = "galaxy.qq.user.keys"

    _template_code = "QQ_SMS_148380455"

    def send_verification_code(
        self, mobile, unlink_failed=False, unlink_sent=True, raise_exception=False
    ):
        template = self.env["sms.template"].search([("code", "=", self._template_code)])
        if template:
            verification_code = self.qq_user_id.generate_verification_code(mobile)
            params = template._render_field(
                "template_param", [self.id], compute_lang=True
            )[self.id]
            aliyun_data = [
                {
                    "res_id": self.id,
                    "number": mobile,
                    "content": params,
                    "code": template.aliyun_code,
                    "sign_name": template.sign_name,
                }
            ]

            try:
                aliyun_result = self.env["galaxy.aliyun.sms.api"]._send_sms_batch(
                    aliyun_data
                )

                _logger.info(
                    "Send batch %s SMS: %s: gave %s",
                    len(self.ids),
                    self.ids,
                    aliyun_result,
                )

                return verification_code
            except Exception as e:
                _logger.info(
                    "Sent batch %s SMS: %s: failed with exception %s",
                    len(self.ids),
                    self.ids,
                    e,
                )
                if raise_exception:
                    raise
