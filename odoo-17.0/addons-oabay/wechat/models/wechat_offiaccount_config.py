# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from ..rpc import wechat_entry

_logger = logging.getLogger(__name__)


class WechatOffiaccountConfig(models.Model):
    _name = 'wechat.offiaccount.config'
    _description = 'Wechat Offiaccount Config'
    _inherit = ['wechat.config.mixin', 'qr.login.provider.mixin', 'mail.thread',
                'mail.activity.mixin', 'image.mixin']

    offiaccount_type = fields.Selection(
        string="公众号类型",
        selection=[
            ('subscribe', '订阅号'),
            ('service', '服务号'),
        ], default='subscribe', required=True)

    menu_ids = fields.One2many(
        'wechat.offiaccount.config.menu', 'offiaccount_id', string='自定义菜单')
    offiaccount_user_ids = fields.One2many(
        'wechat.offiaccount.user', 'offiaccount_id', string='订阅用户')
    offiaccount_taglist_ids = fields.One2many(
        'wechat.offiaccount.taglist', 'offiaccount_id', string='用户标签')
    offiaccount_group_ids = fields.One2many(
        'wechat.offiaccount.group', 'offiaccount_id', string='用户组')

    subscribers_count = fields.Integer(
        "关注数", compute="_compute_user_count")
    taglist_count = fields.Integer("标签列表", compute="_compute_user_count")
    groups_count = fields.Integer("用户组", compute="_compute_user_count")

    # TODO: 同步菜单
    def sync_menu(self):
        self.ensure_one()

        entry = wechat_entry.retrieve_wechat_entry(
            self.env, self.app_id)
        if not entry.app_id:
            raise ValidationError(
                _('Wechat Offiaccount Uninitialized'))

        for menu in self.menu_ids:
            menu.sync_offiaccount_menu(entry)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("同步成功"),
            }
        }

    def retrieve_entry(self, app_id=None, website_id=None):
        from ..rpc import wechat_entry

        if app_id:
            wechat_offiaccount = self.search([('app_id', '=', app_id)])
        elif website_id:
            wechat_offiaccount = self.search(
                [('website_id', '=', website_id), ('is_default', '=', True)], limit=1)
        else:
            wechat_offiaccount = self.search(
                [('is_default', '=', True)], limit=1)
        return wechat_offiaccount, wechat_entry.retrieve_wechat_entry(self.env, wechat_offiaccount.app_id)

    @api.depends('offiaccount_user_ids', 'offiaccount_taglist_ids', 'offiaccount_group_ids')
    def _compute_user_count(self):
        for offiaccount in self:
            offiaccount.update({
                'subscribers_count': len(offiaccount.offiaccount_user_ids.ids),
                'taglist_count': len(offiaccount.offiaccount_taglist_ids.ids),
                'groups_count': len(offiaccount.offiaccount_group_ids.ids)
            })

    @api.constrains('qr_login_id', 'offiaccount_type', 'is_default')
    def _check_only_service_type_can_login(self):
        for config in self:
            if config.qr_login_id and (config.offiaccount_type != 'service' or not config.is_default):
                raise ValidationError(
                    _("Only Offiaccount with the type of service and is default can be set to login."))

    @api.constrains('website_id', 'is_default')
    def _check_only_one_default(self):
        """ Do not allow one website with two default weapp config """
        self.flush_recordset(['website_id', 'is_default'])
        self.env.cr.execute(
            """SELECT website_id
                 FROM wechat_offiaccount_config
                WHERE website_id IN (select website_id from wechat_offiaccount_config where id IN %s AND is_default=true) 
                 AND is_default=true 
             GROUP BY website_id
               HAVING COUNT(*) > 1
            """,
            (tuple(self.ids),)
        )
        if self.env.cr.rowcount:
            raise ValidationError(
                _("A website only can has one default config."))

    def view_subscribers(self):
        self.ensure_one()

        return {
            'name': _('公众号订阅用户'),
            'res_model': 'wechat.offiaccount.user',
            # 'res_model': 'res.partner',
            'view_mode': 'kanban',
            'type': 'ir.actions.act_window',
            'context': dict(
                self.env.context,
                offiaccount_id=self.id,
            ),
            'domain': [('offiaccount_id.id', '=', self.id)],
            'target': 'new',
            'help': """
                <p class="o_view_nocontent_empty_folder">Current Offiaccount Has No Subscriber</p>
                """
        }

    def view_taglist(self):
        self.ensure_one()

        return {
            'name': _('标签列表'),
            'view_mode': 'tree',
            'res_model': 'wechat.offiaccount.taglist',
            'type': 'ir.actions.act_window',
            'context': dict(
                self.env.context,
                offiaccount_id=self.id,
            ),
            'domain': [('offiaccount_id', '=', self.id)],
            'target': 'new',
            'help': """
                <p class="o_view_nocontent_empty_folder">当前公众号未设置标签</p>
                <p>您可在此添加标签</p>
                """
        }

    @api.model
    def view_groups(self, args):
        offiaccount = self.browse(args)
        if offiaccount.exists():
            return {
                'name': _('Offiaccount Groups'),
                'view_mode': 'list',
                'res_model': 'wechat.offiaccount.group',
                'type': 'ir.actions.act_window',
                'context': dict(
                    self.env.context,
                    offiaccount_id=offiaccount.id,
                ),
                'domain': [('offiaccount_id.id', '=', offiaccount.id)],
                'target': 'new',
                'help': """
                    <p class="o_view_nocontent_empty_folder">Current Offiaccount Has No Groups</p>
                    <p>you can add group with mp site.</p>
                    """
            }


class WechatOffiaccountMenu(models.Model):
    _name = 'wechat.offiaccount.config.menu'
    _description = '公众号菜单'

    offiaccount_id = fields.Many2one(
        'wechat.offiaccount.config', required=True, string='微信公众号', ondelete='cascade')
    menu_id = fields.Many2one(
        'wechat.menu', required=True, string='自定义菜单', ondelete='cascade')
    tag_id = fields.Many2one('wechat.offiaccount.taglist', string='选择标签')
    offiaccount_menuid = fields.Char('微信菜单唯一标识')

    def sync_offiaccount_menu(self, entry):
        self.ensure_one()

        json_data = self.menu_id.to_json()
        if self.tag_id:
            json_data.update({
                'matchrule': {
                    'tag_id': self.tag_id.offiaccount_tag_id
                }
            })

            menu_result = entry.client.menu.add_conditional(json_data)
            self.offiaccount_menuid = menu_result.get('menuid')
        else:
            menu_result = entry.client.menu.create(json_data)

        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'type': 'success',
        #         'message': _("同步成功"),
        #     }
        # }
