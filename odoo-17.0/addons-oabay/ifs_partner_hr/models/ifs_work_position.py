# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, Command


class InclusiveFinancingWorkPosition(models.Model):
    _inherit = 'ifs.work.position'

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'company_id' in defaults and 'category_ids' in fields_list:
            company = self.env['res.company'].browse(
                defaults.get('company_id'))
            defaults.update({
                'category_ids': [self.env.ref(
                    f'ifs_partner.module_category_ifs_partner_{p}').id for p in (company.ifs_partners or [])]
            })

        return defaults

    @api.depends('company_id', 'company_id.ifs_partners')
    def _compute_category_ids(self):
        for record in self:
            record.category_ids = []
            if record.company_id.ifs_partners:
                record.category_ids = list(map(
                    lambda p: self.env.ref(
                        f'ifs_partner.module_category_ifs_partner_{p}').id, record.company_id.ifs_partners))

    @api.model
    def create_default_wp(self, company, current_ifs_partner):
        wp_sudo = self.sudo()
        manager_wp = wp_sudo.search([
            ('company_id', '=', company.id),
            ('code', '=', 'SYSTEM')
        ])
        if not manager_wp.exists():
            manager_wp = wp_sudo.create({
                'name': '系统管理员',
                'code': 'SYSTEM',
                'company_id': company.id,
                'groups_id': [Command.set([self.env.ref(
                        f'ifs_partner.group_ifs_partner_{ifs_partner}_system').id
                    for ifs_partner in (company.ifs_partners or [])])]
            })
        elif current_ifs_partner and current_ifs_partner in (company.ifs_partners or []):
            manager_wp.with_context(force=True).write({
                'groups_id': [
                    Command.link(self.env.ref(
                        f'ifs_partner.group_ifs_partner_{current_ifs_partner}_system').id)
                ]
            })

        return manager_wp

    @api.model
    def unlink_ifs_partner_wp(self, company_id, ifs_partner):
        partner_wps = self.sudo().search([
            ('company_id', '=', company_id),
        ])
        partner_groups = self.env['res.groups'].sudo().search([
            ('category_id', '=', self.env.ref(
                f'ifs_partner.module_category_ifs_partner_{ifs_partner}').id)
        ])
        for partner_wp in partner_wps:
            partner_wp.with_context(force=True).write({
                'groups_id': [
                    Command.unlink(group_id) for group_id in partner_groups.ids
                ] + [Command.unlink(self.env.ref(
                    f'ifs_partner.group_ifs_partner_{ifs_partner}_system'
                ).id)]
            })

    def write(self, vals):
        if self.code == 'SYSTEM' and 'groups_id' in vals and not self._context.get('force', False):
            # 系统管理员的权限不允许修改
            vals.pop('groups_id')
        return super().write(vals)
