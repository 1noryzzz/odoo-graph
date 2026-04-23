# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from ..rpc import wechat_entry

_logger = logging.getLogger(__name__)

MENU_TYPE = [
    ('wechat.menu.item.click', '点击事件'),
    ('wechat.menu.item.view', '跳转链接'),
    ('wechat.menu.item.article', '下发图文'),
    ('wechat.menu.item.media', '下发素材'),
    ('wechat.menu.item.miniprogram', '打开小程序'),
    ('wechat.menu.item.scancode', '扫码'),
]


class WechatMenu(models.Model):
    _name = 'wechat.menu'
    _description = '微信菜单'
    _inherit = ['mail.thread', 'image.mixin']

    name = fields.Char('菜单名称')
    menu_item_ids = fields.One2many(
        'wechat.menu.item', 'menu_id', string='菜单项')

    @api.constrains("menu_item_ids")
    def _check_menu_item_ids(self):
        if len(self.menu_item_ids) > 3:
            raise ValidationError(_('当前菜单项不能超过三条！'))

    def to_json(self):
        self.ensure_one()

        return {
            'button': self.menu_item_ids.mapped(
                lambda item: item.to_json()
            )
        }


class WechatMenuItem(models.Model):
    _name = 'wechat.menu.item'
    _description = '微信菜单项'
    _inherit = ['mail.thread']
    _order = "sequence"

    menu_id = fields.Many2one('wechat.menu', string='自定义菜单')
    sequence = fields.Integer(string='显示顺序', help="菜单项目显示顺序", default=10)
    name = fields.Char('菜单项名称', required=True)
    parent_id = fields.Many2one(
        'wechat.menu.item', string='上级菜单', index=True, ondelete='set null')
    child_ids = fields.One2many('wechat.menu.item', 'parent_id', string='子菜单项')
    type = fields.Reference(selection=MENU_TYPE, string='类型')

    def to_json(self):
        self.ensure_one()

        if len(self.child_ids or []) > 0:
            return {
                'name': self.name,
                'sub_button': self.child_ids.mapped(
                    lambda item: item.to_json()
                )
            }
        else:
            json_str = self.type.to_json()
            json_str.update({
                'name': self.name
            })
            return json_str


class WechatMenuItemActionMixin(models.AbstractModel):
    _name = 'wechat.menu.item.action'

    name = fields.Char('菜单动作名称')


class WechatMenuItemClick(models.Model):
    _name = 'wechat.menu.item.click'
    _inherit = ['wechat.menu.item.action']
    _description = '菜单点击事件'

    key = fields.Char('事件Key', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'type': 'click',
            'key': self.key
        }


class WechatMenuItemView(models.Model):
    _name = 'wechat.menu.item.view'
    _inherit = ['wechat.menu.item.action']
    _description = '链接跳转'

    url = fields.Char('链接地址', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'type': 'view',
            'url': self.url
        }


class WechatMenuItemArticle(models.Model):
    _name = 'wechat.menu.item.article'
    _inherit = ['wechat.menu.item.action']
    _description = '触发图文消息事件'

    article_id = fields.Char('图文ID', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'type': 'article_id',
            'article_id': self.article_id
        }


class WechatMenuItemMedia(models.Model):
    _name = 'wechat.menu.item.media'
    _inherit = ['wechat.menu.item.action']
    _description = '触发图文消息事件'

    media_id = fields.Char('素材ID', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'type': 'media_id',
            'media_id': self.media_id
        }


class WechatMenuItemMiniprg(models.Model):
    _name = 'wechat.menu.item.miniprogram'
    _inherit = ['wechat.menu.item.action']
    _description = '打开小程序'

    appid = fields.Char('小程序的appid', required=True)
    url = fields.Char('小程序内地址', required=True)
    pagepath = fields.Char('小程序的页面路径', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'type': 'miniprogram',
            'appid': self.appid,
            'url': self.url,
            'pagepath': self.pagepath
        }


class WechatMenuItemScancode(models.Model):
    _name = 'wechat.menu.item.scancode'
    _inherit = ['wechat.menu.item.action']
    _description = '打开扫码'

    #TODO: 未实现
    key = fields.Char('事件Key', required=True)

    def to_json(self):
        self.ensure_one()
        return {
            'key': self.key
        }
