# -*- coding: utf-8 -*-

import logging

from odoo import _, api, models, fields


_logger = logging.getLogger(__name__)


class InclusiveFinancingPartnerMixin(models.AbstractModel):
    _name = 'ifs.partner.mixin'
    _inherit = ['ifs.ir.sequence.mixin', 'mail.thread', 'mail.activity.mixin']
    _inherits = {'ifs.base.company': 'ifs_company_id'}
    _description = '业务参与方mixin'
    _ifs_partner = False

    state = fields.Selection([
        ('normal', '正常'),
        ('paused', '暂停'),
    ], string='状态', default='normal')
    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    json_datas = fields.Properties(
        '工商登记信息', definition='definition_id.params_definition', related='ifs_company_id.json_datas')
    practice_info = fields.Properties(
        '医疗机构执业许可证结果数据', definition='practice_definition_id.params_definition', related='ifs_company_id.practice_info')

    def unlink(self):
        ifs_partner = self._ifs_partner
        ifs_company_ids = self.mapped('ifs_company_id')

        res = super().unlink()
        for ifs_company in ifs_company_ids:
            ifs_company.inactive_ifs_partner(ifs_partner)

        return res
