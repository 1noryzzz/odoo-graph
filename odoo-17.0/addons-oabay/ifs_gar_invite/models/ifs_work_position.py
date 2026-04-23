# -*- coding: utf-8 -*-
import logging

from odoo import _, api, models, Command

_logger = logging.getLogger(__name__)


class InclusiveFinancingWorkPosition(models.Model):
    _inherit = 'ifs.work.position'

    @api.model
    def create_default_wp(self, company_id, current_ifs_partner):
        manager_wp = super().create_default_wp(company_id, current_ifs_partner)
        if self._context.get('invite'):
            manager_wp.with_context(force=True).write({
                'groups_id': [
                    Command.link(self.env.ref(
                        f'ifs_gar_invite.group_ifs_gar_{current_ifs_partner}_entry').id)
                ]
            })
        elif self._context.get('entry_pass'):
            manager_wp.with_context(force=True).write({
                'groups_id': [
                    Command.unlink(self.env.ref(
                        f'ifs_gar_invite.group_ifs_gar_{current_ifs_partner}_entry').id)
                ]
            })

        return manager_wp

    @api.model
    def unlink_ifs_partner_wp(self, company_id, ifs_partner):
        super().unlink_ifs_partner_wp(company_id, ifs_partner)

        system_wp = self.sudo().search([
            ('company_id', '=', company_id),
            ('code', '=', 'SYSTEM')
        ], limit=1)
        group_id = self.env.ref(
            f'ifs_gar_invite.group_ifs_gar_{ifs_partner}_entry', raise_if_not_found=False)

        if system_wp.exists() and group_id and group_id.id:
            system_wp.with_context(force=True).write({
                'groups_id': [
                    Command.unlink(group_id.id)
                ]
            })
