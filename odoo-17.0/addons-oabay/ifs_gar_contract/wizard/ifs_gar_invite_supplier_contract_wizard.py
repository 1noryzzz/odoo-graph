# -*- coding: utf-8 -*-

import json
from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecInviteSupplierContractWizard(models.TransientModel):
    _name = 'ifs.gar.invite.supplier.contract.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '邀请供应方向导--合同预览'
    _step_models = [
        'ifs.gar.invite.supplier.wizard',
        'ifs.gar.invite.supplier.fee.wizard',
        'ifs.gar.invite.supplier.contract.wizard',
        'ifs.gar.invite.supplier.root.user.wizard',
    ]

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'ifs_company_id' in fields and res.get('ifs_company_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                invite_supplier = self.env['ifs.gar.invite.supplier'].search([
                    ('ifs_company_id', '=', res.get('ifs_company_id')),
                    ('factor_id.company_id', '=', self.env.company.id)
                ], limit=1)
                if invite_supplier.id:
                    if not invite_supplier.t17_contract_info_id.id:
                        template_id = self.env['ifs.contract.template'].retrieve_by_code('T17', invite_supplier.factor_id.id)
                        invite_supplier.t17_contract_info_id = self.env['ifs.contract.info'].sudo().create({
                            'name': template_id.name,
                            'partner_one': '%s,%d' % (invite_supplier._name, invite_supplier.id),
                            'partner_two': '%s,%d' % (invite_supplier.factor_id._name, invite_supplier.factor_id.id),
                            'partner_one_signature': False,
                            'partner_two_signature': invite_supplier.factor_id.signature,
                            'template_id': template_id.id,
                            'params': json.dumps({
                                'product_scope': '等待供应方进件后填写',
                                'contract_total_quota': 10000,
                                'fee_solution_contract_content': invite_supplier.fee_solution_id.contract_content,
                            }),
                        })

                    res.setdefault(
                        't17_contract_info_id',
                        invite_supplier.t17_contract_info_id.id)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可预览合同！'))
        return res

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    logo = fields.Binary(string="公司Logo", related='ifs_company_id.logo')
    t17_contract_info_id = fields.Many2one('ifs.contract.info', string='总额度合同')
    report_content = fields.Html(
        '合同内容', related='t17_contract_info_id.report_content',
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
