# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class QrLoginProvider(models.Model):
    _inherit = "qr.login.provider"

    work_agent_ids = fields.One2many(
        'wechat.work.agent.config', 'qr_login_id', string='Work Agents for Login')
    offiaccount_ids = fields.One2many(
        'wechat.offiaccount.config', 'qr_login_id', string='Offiaccounts')

    @api.depends('work_agent_ids', 'offiaccount_ids')
    def _compute_is_binded(self):
        super(QrLoginProvider, self)._compute_is_binded()
        for p in self:
            if len(p.work_agent_ids.ids) > 0 or len(p.offiaccount_ids.ids) > 0:
                p.is_binded = True
                
    # @api.constrains('work_agent_ids', 'enabled')
    # def _check_only_one_for_work_be_enabled(self):
    #     self.flush(['work_agent_ids', 'enabled'])
    #     self.env.cr.execute(
    #         """SELECT work_id 
    #              FROM wechat_work_agent_config wwac 
    #              LEFT JOIN qr_login_provider qlp ON qlp.id=wwac.qr_login_id 
    #             WHERE qlp.enabled = true AND work_id IN 
    #              (SELECT work_id FROM wechat_work_agent_config WHERE qr_login_id IN %s)
    #          GROUP BY work_id
    #            HAVING COUNT(*) > 1
    #         """,
    #         (tuple(self.ids),)
    #     )
    #     if self.env.cr.rowcount:
    #         raise ValidationError(
    #             _("一个企业微信号，只能有一个激活的二维码登录设置！"))
