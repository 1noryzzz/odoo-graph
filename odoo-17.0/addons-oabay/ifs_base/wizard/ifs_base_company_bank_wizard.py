# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class InclusiveFinancingBaseCompanyBankWizard(models.AbstractModel):
    _name = 'ifs.base.company.bank.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '公司结算账号添加'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')

    bank_id = fields.Many2one('res.bank', string='开户行', required=True)
    acc_number = fields.Char('账号', required=True)
    deposit_license = fields.Binary(string='开户证可证')

    def action_confirm(self):
        partner_bank_info = {
            'bank_id': self.bank_id.id,
            'acc_number': self.acc_number,
            'sequence': 1,
            'currency_id': self.env.company.currency_id.id,
        }
        self.ifs_company_id.write({
            'deposit_license': self.deposit_license,
            'bank_ids': [fields.Command.update(
                self.ifs_company_id.acquiescence_bank_id.id, partner_bank_info)]
            if self.ifs_company_id.acquiescence_bank_id else [
                fields.Command.create(partner_bank_info)],
        })
