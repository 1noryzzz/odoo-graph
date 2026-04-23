# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields
from random import randint
from pypinyin import Style, lazy_pinyin


class GalaxyExternalApiCategory(models.Model):
    _name = 'galaxy.external.api.category'
    _description = '外部API类别'
    _order = "sequence, create_date"
    _rec_names_search = ['name', 'code']

    _sql_constraints = [
        ('code_uniq', 'unique (code)', '类别代码已存在！'),
        ('name_uniq', 'unique (name)', '类别名称已存在！')
    ]

    code = fields.Char(
        compute='_compute_code', string='类别代码', store=True, index=True)
    name = fields.Char('类别名称', required=True, index=True)
    sequence = fields.Integer('排序', default=100)
    api_ids = fields.One2many(
        'galaxy.external.api', 'category_id', string='接口列表')
    api_count = fields.Integer(compute='_compute_api_count', string='接口数')
    remark = fields.Text('类别说明')

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            if record.name:
                record.code = ''.join(list(map(lambda x: x.upper(), lazy_pinyin(
                    record.name, style=Style.FIRST_LETTER))))

    @api.depends('api_ids')
    def _compute_api_count(self):
        for record in self:
            record.api_count = 0
            if record.api_ids:
                record.api_count = len(record.api_ids.ids)


class GalaxyExternalApiTag(models.Model):
    _name = 'galaxy.external.api.tag'
    _description = '外部API标签'
    _order = "sequence, create_date"

    _sql_constraints = [
        ('name_uniq', 'unique (name)', '标签名称已存在！')
    ]

    def _get_default_color(self):
        return randint(1, 11)

    sequence = fields.Integer('排序', default=100)
    name = fields.Char('标签名称', required=True)
    color = fields.Integer(string='标签颜色', default=_get_default_color)
