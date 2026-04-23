# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingBaseCompanyContactWizard(models.AbstractModel):
    _name = 'ifs.base.company.contact.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '公司联系人添加'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
