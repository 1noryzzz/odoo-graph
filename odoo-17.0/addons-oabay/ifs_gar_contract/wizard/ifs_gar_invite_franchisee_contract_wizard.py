# -*- coding: utf-8 -*-

import json
from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecInviteFranchiseeContractWizard(models.TransientModel):
    _name = 'ifs.gar.invite.franchisee.contract.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '邀请合伙人向导--合同预览'
    _step_models = [
        'ifs.gar.invite.franchisee.wizard',
        'ifs.gar.invite.franchisee.contract.wizard',
        'ifs.gar.invite.franchisee.root.user.wizard',
    ]

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'ifs_company_id' in fields and res.get('ifs_company_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                invite_franchisee = self.env['ifs.gar.invite.franchisee'].search([
                    ('ifs_company_id', '=', res.get('ifs_company_id')),
                    ('factor_id.company_id', '=', self.env.company.id)
                ], limit=1)
                if invite_franchisee.id:
                    if not invite_franchisee.p01_contract_info_id.id:
                        template_id = self.env['ifs.contract.template'].retrieve_by_code('P01', invite_franchisee.factor_id.id)
                        invite_franchisee.p01_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                            'name': template_id.name,
                            'partner_one': '%s,%d' % (invite_franchisee.factor_id._name, invite_franchisee.factor_id.id),
                            'partner_two': '%s,%d' % (invite_franchisee._name, invite_franchisee.id),
                            'partner_one_signature': False,
                            'partner_two_signature': invite_franchisee.factor_id.signature,
                            'template_id': template_id.id,
                            'params': json.dumps({
                                'franchisee_type_value': '11111',
                                'franchisee_type': '1111',
                                'province': str('广东省').replace('省', '').replace('市', ''),
                                'city': str('深圳市').replace('市', ''),
                                'area_agency_fee': '11111',
                                'first_year_base_service_fee': '11111%',
                                'first_year_trade_service_fee': '11111%',
                                'follow_up_base_service_fee': '11111%',
                                'follow_up_trade_service_fee': '11111%',
                            }),
                        })

                    res.setdefault(
                        'p01_contract_info_id',
                        invite_franchisee.p01_contract_info_id.id)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可预览合同！'))
        return res

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
    p01_contract_info_id = fields.Many2one('ifs.contract.info', string='事业合伙人合作协议')
    report_content = fields.Html(
        '合同内容', related='p01_contract_info_id.report_content',
        render_engine='qweb', translate=True, sanitize=False)

    def action_confirm(self):
        if self.is_in_step and self._context.get('next_model', False):
            return {
                'name': self.env[self._next_model(self._name)]._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': self._next_model(self._name),
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                    'prev_model': self._name,
                    'next_model': self._next_model(self._next_model(self._name)),
                }
            }
