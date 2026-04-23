# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingPartnerChannelsp(models.Model):
    _name = 'ifs.partner.channelsp'
    _description = '渠道服务商信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'channelsp'

    @api.model_create_multi
    def create(self, vals_list):
        channelsps = super().create(vals_list)
        for channelsp in channelsps:
            channelsp.ifs_company_id.active_ifs_partner(channelsp._ifs_partner)

        return channelsps
