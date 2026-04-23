# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError

class InclusiveFinancingPartnerFunder(models.Model):
    _name = 'ifs.partner.funder'
    _description = '资金方基本信息'
    _inherit = ['ifs.partner.mixin']
    _ifs_partner = 'funder'
    

    type = fields.Selection([('bank', '银行'), ('microfinance', '小贷'),
                            ('private', '私募'), ('vc', '风险投资')], required=True, string="资金方类型")
    
    def action_certificate_company(self):
        for record in self:
            record.ifs_company_id.certificate_company()

    @api.model_create_multi
    def create(self, vals_list):
       
        funders = super().create(vals_list)
        for funder in funders:
            funder.ifs_company_id.active_ifs_partner(funder._ifs_partner)

        return funders

    def action_create_business_license(self):
        return {
            'name': _('更新营业执照'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.funder.business.license.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }

    def action_update_account(self):
        return {
            'name': _('更新银行账户'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.partner.funder.bank.wizard',
            'target': 'new',
            'context': {
                'default_ifs_company_id': self.ifs_company_id.id,
            }
        }
