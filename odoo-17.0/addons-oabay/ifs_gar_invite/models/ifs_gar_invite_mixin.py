# -*- coding: utf-8 -*-

import logging

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecInviteMixin(models.AbstractModel):
    _name = 'ifs.gar.invite.mixin'
    _inherit = ['ifs.ir.sequence.mixin']
    _inherits = {'ifs.base.company': 'ifs_company_id'}
    _description = '邀请注册的基本信息'
    _order = 'create_date desc'
    _invite_ifs_partner = False

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    json_datas = fields.Properties(
        '工商登记信息', definition='definition_id.params_definition', related='ifs_company_id.json_datas')
    invite_date = fields.Datetime('邀请发出日期', copy=False)

    def start_invite(self):
        raise AccessDenied(_('邀请注册功能未实现'))

    @api.model_create_multi
    def create(self, vals_list):
        invites = super().create(vals_list)
        for invite in invites:
            self.env['ifs.work.position'].with_context(
                invite=True).create_default_wp(invite.company_id, invite._invite_ifs_partner)

        return invites
