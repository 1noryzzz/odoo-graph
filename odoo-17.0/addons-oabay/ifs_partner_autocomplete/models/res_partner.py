# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _update_autocomplete_data(self, vat):
        # 覆盖掉异步刷新信息的方法
        pass

    @api.model
    def enrich_company(self, company_domain, partner_gid, vat, timeout=15):
        # 覆盖掉从IAP获取信息的方法
        return {}

    @api.model
    def enrich_by_duns(self, duns, timeout=15):
        return {}

    @api.model
    def enrich_by_gst(self, gst, timeout=15):
        return {}
