# -*- coding: utf-8 -*-

import json
from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecInviteLawfirmContractWizard(models.TransientModel):
    _name = 'ifs.gar.invite.lawfirm.contract.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '邀请律师事务所向导--合同预览'
    _step_models = [
        'ifs.gar.invite.lawfirm.wizard',
        'ifs.gar.invite.lawfirm.contract.wizard',
        'ifs.gar.invite.lawfirm.root.user.wizard',
    ]

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'ifs_company_id' in fields and res.get('ifs_company_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                invite_lawfirm = self.env['ifs.gar.invite.lawfirm'].search([
                    ('ifs_company_id', '=', res.get('ifs_company_id')),
                    ('factor_id.company_id', '=', self.env.company.id)
                ], limit=1)
                if invite_lawfirm.id:
                    if not invite_lawfirm.p10_contract_info_id.id:
                        template_id = self.env['ifs.contract.template'].retrieve_by_code('P10', invite_lawfirm.factor_id.id)
                        invite_lawfirm.p10_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                            'name': template_id.name,
                            'partner_one': '%s,%d' % (invite_lawfirm.factor_id._name, invite_lawfirm.factor_id.id),
                            'partner_two': '%s,%d' % (invite_lawfirm._name, invite_lawfirm.id),
                            'partner_one_signature': invite_lawfirm.factor_id.signature,
                            'partner_two_signature': False,
                            'template_id': template_id.id,
                        })

                    res.setdefault(
                        'p10_contract_info_id',
                        invite_lawfirm.p10_contract_info_id.id)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可预览合同！'))
        return res

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
    p10_contract_info_id = fields.Many2one('ifs.contract.info', string='保理方与律师事务所合作框架协议')
    report_content = fields.Html(
        '合同内容', related='p10_contract_info_id.report_content',
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
