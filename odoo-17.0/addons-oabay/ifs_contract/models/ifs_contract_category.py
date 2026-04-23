# -*- coding: utf-8 -*-


from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from random import randint

class InclusiveFinancingContractCategory(models.Model):
    _name = 'ifs.contract.category'
    _description = '合同分类'
    _order = 'code'

    _sql_constraints = [
        ('code_uniq', 'unique (code)', '合同分类编码已存在！')
    ]

    code = fields.Char('分类编码', required=True, index=True, help="合同分类被引用时的唯一编号")
    name = fields.Char('分类名称', required=True)
    sequence = fields.Integer('排序', default=100)
    contract_template_ids = fields.One2many('ifs.contract.template','category_id',string="合同列表")
    contract_count = fields.Integer(compute='_compute_contract_count', string='接口数')
    remark = fields.Text('类别说明')
    
    @api.depends('contract_template_ids')
    def _compute_contract_count(self):
        for record in self:
            record.contract_count = 0
            if record.contract_template_ids:
                record.contract_count = len(record.contract_template_ids.ids)
                

class InclusiveFinancingContractTag(models.Model):
    _name = 'ifs.contract.tag'
    _description = '合同标签'
    _order = "sequence, create_date"

    _sql_constraints = [
        ('name_uniq', 'unique (name)', '标签名称已存在！')
    ]

    def _get_default_color(self):
        return randint(1, 11)

    sequence = fields.Integer('排序', default=100)
    name = fields.Char('标签名称', required=True)
    color = fields.Integer(string='标签颜色', default=_get_default_color)
