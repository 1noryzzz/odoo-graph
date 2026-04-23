# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingBaseCompanyWizard(models.AbstractModel):
    _name = 'ifs.base.company.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '金融业务的参与公司添加'

    name = fields.Char(string='公司名称', required=True)
    email = fields.Char(string='邮箱', required=True)
    phone = fields.Char(string='电话', required=True)
    company_registry = fields.Char(string='统一社会信用代码', required=True)
    logo = fields.Binary(string="公司Logo")
    street = fields.Char(string='地址')

    @api.depends('company_registry')
    def _compute_current_step(self):
        super()._compute_current_step()
        for record in self:
            if record.company_registry:
                record.current_step = 2

                # 当前记录的信息是从前端取到的，但这里再查询一下，
                # 如果已有此公司的信息，则优先使用已有的信息
                ifs_company = self.env['ifs.base.company'].search([
                    ('company_registry', '=', record.company_registry)
                ], limit=1)
                if ifs_company.exists():
                    record.update({
                        'email': ifs_company.email or record.email,
                        'phone': ifs_company.phone or record.phone,
                        'logo': record.logo or ifs_company.logo,
                        'street': ifs_company.street or record.street,
                    })
            else:
                record.current_step = 1

    def action_confirm(self):
        company_info = self.read(
            ['name', 'email', 'phone', 'company_registry', 'logo', 'street'])[0]
        company_info.pop('id')
        company_info.update({
            'business_address': company_info.get('street')
        })

        return self.env['ifs.base.company'].sync_business_registration(company_info)

    def nosave_redo(self):
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'new',
            'context': self._context
        }
