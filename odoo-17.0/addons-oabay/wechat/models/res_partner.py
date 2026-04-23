# -*- coding: utf-8 -*-

from odoo import fields, models


class Partner(models.Model):

    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[
        ('wechat', 'Wechat Offiaccount'), ('weapp', 'WeApp'),
        ('wework', 'Wechat Work')])
    union_id = fields.Char('UnionId', readonly=True)
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='Gender')
    area_id = fields.Many2one(
        "res.country.area", string='Area', ondelete='restrict',
        domain="[('state_id', '=?', state_id)]")

    is_default_addr = fields.Boolean('Is Default Address')

    offiaccount_user_ids = fields.One2many(
        'wechat.offiaccount.user', 'partner_id', string='Offiaccount Users', auto_join=True)
    weapp_user_ids = fields.One2many(
        'wechat.weapp.user', 'partner_id', string='Weapp Users', auto_join=True)
    work_external_user_ids = fields.One2many(
        'wechat.work.external.user', 'partner_id', string='Work External Users', auto_join=True)

    _sql_constraints = [(
        'wechat_union_id_unique',
        'UNIQUE (union_id)',
        'wechat user union_id is existed！'
    )]
