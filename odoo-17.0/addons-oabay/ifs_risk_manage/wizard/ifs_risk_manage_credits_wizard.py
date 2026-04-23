# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingRiskManageCreditsWizard(models.TransientModel):
    _name = 'ifs.risk.manage.credits.wizard'
    _description = '个人征信向导'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True, string='金融业务参与方')
    company_id = fields.Many2one(
        'res.company', related='ifs_company_id.company_id', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string='被查询人', compute='_compute_employee_id', ondelete='restrict', required=True, readonly=False)
    employee_name = fields.Char(
        string='姓名', related='employee_id.name')
    idcard = fields.Char(
        string='身份证号', related='employee_id.identification_id')
    mobile = fields.Char(
        string='手机号', related='employee_id.mobile_phone')

    def action_confirm(self):
        credits_info = self.read(
            ['idcard', 'mobile'])[0]
        credits_info.pop('id')
        credits_info.update({
            'ifs_company_id': self.ifs_company_id.id,
            'name': self.employee_id.name,
            # 'last_fetch_credit_time': fields.Datetime.now()
        })
        credits = self.env['ifs.risk.manage.credits'].create(credits_info)
        return {
            'name': self.env['ifs.risk.manage.credits']._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.risk.manage.credits',
            'target': 'current',
            'res_id': credits.id,
        }

    @api.depends('company_id')
    def _compute_employee_id(self):
        self.employee_id = self.env['hr.employee'].with_company(
            self.company_id).search([('company_id', '=', self.company_id.id)]).id
