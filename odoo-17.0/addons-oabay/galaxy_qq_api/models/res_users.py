# -*- coding: utf-8 -*-

from odoo import api, models, _


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def qqapi_signup(self, email, access_key):
        values = {
            "login": email,
            "name": email,
            "email": email,
            "country_id": access_key.country_id.id if access_key.country_id else False,
            "city": access_key.city,
            "zip": access_key.postal,
            "tz": access_key.tz,
        }
        params = access_key.params

        if params:
            if params.get("nickname"):
                values["name"] = params["nickname"]
            if params.get("country_code"):
                values["country_id"] = (
                    self.env["res.country"]
                    .search([("code", "=", params["country_code"])], limit=1)
                    .id
                )
            if params.get("lang"):
                supported_lang_codes = [
                    code for code, _ in self.env["res.lang"].get_installed()
                ]
                if params.get("lang") in supported_lang_codes:
                    values["lang"] = params.get("lang")
            if params.get("tz"):
                values["tz"] = params.get("tz")

            return self._signup_create_user(values)

        return False
