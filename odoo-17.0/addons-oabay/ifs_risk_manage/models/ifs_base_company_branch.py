# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingBaseCompanyBranch(models.Model):
    _name = 'ifs.base.company.branch'
    _description = '金融业务的参与公司的分支机构信息'
    _order = 'ifs_company_id, branch_id'
    _rec_name = 'name'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', string='参与公司', required=True, ondelete='cascade')
    branch_id = fields.Many2one(
        'ifs.base.company', string='分支机构', required=True, ondelete='restrict')
    name = fields.Char('公司名称', related='branch_id.name')
    is_investment = fields.Boolean('是否为对外投资', default=True)
    share_ratio = fields.Percent('投资占比', digits=(
        16, 2), required=True, default=1)
