# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Country(models.Model):
    _inherit = ['res.country']

    area_ids = fields.One2many(
        'res.country.area', 'country_id', string='Area Code')


class CountryState(models.Model):
    _inherit = ['res.country.state']

    area_ids = fields.One2many(
        'res.country.area', 'state_id', string='Area Code')


class CountryArea(models.Model):
    _description = "Country Area"
    _name = 'res.country.area'
    _order = 'code'

    country_id = fields.Many2one(
        'res.country', string='国家', required=True)
    state_id = fields.Many2one(
        'res.country.state', string='省', required=True)
    code = fields.Char(
        string='区域代码', help="Area Code Define In GB/T 2260", required=True)
    name = fields.Char(string='Area Name', required=True)
    area_type = fields.Char(
        string='区域类型', store=True, compute='_compute_area_type')
    parent_area_id = fields.Integer(
        string='上级区域', store=True, compute='_compute_area_type')
    revision = fields.Char(string='Revision')

    _sql_constraints = [
        ('area_code_uniq', 'unique(country_id, code)',
         'The code of the area must be unique by country !')
    ]

    @api.depends('code', 'name')
    def _compute_area_type(self):
        for res in self:
            res.parent_area_id = 0
            if res.code[-4:] == '0000':
                if res.name[-1:] == u'市':
                    res.area_type = 'dc'
                    res.parent_area_id = res.id
                else:
                    res.area_type = 'province'
            elif res.code[-2:] == '00':
                res.area_type = 'city'
                province = self.search(
                    [('area_type', '=', 'province'), ('code', 'like', res.code[:2] + '____')])
                if province.exists():
                    res.parent_area_id = province.id
            else:
                res.area_type = 'area'
                city = self.search(
                    ['|', 
                     '&', ('area_type', '=', 'dc'), ('code', 'like', res.code[:2] + '____'), 
                     '&', ('area_type', '=', 'city'), ('code', 'like', res.code[:4] + '__')])
                if city.exists():
                    res.parent_area_id = city.id
