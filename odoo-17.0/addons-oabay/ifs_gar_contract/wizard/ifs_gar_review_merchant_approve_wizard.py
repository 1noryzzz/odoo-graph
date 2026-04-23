# -*- coding: utf-8 -*-

import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecReviewMerchantApprove(models.TransientModel):
    _inherit = 'ifs.gar.review.merchant.approve.wizard'

    def action_confirm(self):
        super().action_confirm()

        factor_supplier = self.env['ifs.gar.partner.factor.supplier'].search([
            ('supplier_id', '=', self.entry_id.supplier_id.id),
            ('factor_id', '=', self.entry_id.factor_id.id),
        ], limit=1)
        if not factor_supplier.id:
            raise AccessDenied(_('无法找到保理方与供应方关联关系'))

        # 买方账款最高子额度合同
        t18_template = self.env['ifs.contract.template'].retrieve_by_code('T18', self.entry_id.factor_id.id)
        t18_contract = self.env['ifs.contract.info'].create({
            'name': t18_template.name,
            'partner_one': '%s,%d' % (self.entry_id._name, self.entry_id.id),
            'partner_two': '%s,%d' % (self.entry_id.factor_id._name, self.entry_id.factor_id.id),
            'partner_two_signature': self.entry_id.factor_id.signature,
            'params': json.dumps({
                'supplier_name': self.entry_id.supplier_id.name,
                'product_scope': factor_supplier.product_scope,
                'approved_quota': self.supplier_final_quota and self.supplier_final_quota/1,
                'supplier_sign_date': fields.Date.to_string(
                    factor_supplier.t17_contract_info_id.sign_date),
            }),
            'template_id': t18_template.id,
        })
        
        # 最高额不可撤销担保书
        t22_template = self.env['ifs.contract.template'].retrieve_by_code('T22', self.entry_id.factor_id.id)
        t22_contract = self.env['ifs.contract.info'].create({
            'name': t22_template.name,
            'partner_one': '%s,%d' % (self.entry_id.root_employee_id.sudo().user_id._name, self.entry_id.root_employee_id.sudo().user_id.id),
            'params': json.dumps({
                'factor_name': self.entry_id.factor_id.name,
                'mer_account_compensation_limit': self.supplier_final_quota or 0,
                'ceiling': self.supplier_final_quota or 0,
                'name': self.entry_id.name,
                'user_name': self.entry_id.legal_name if self.entry_id.is_self_guarantee else self.entry_id.guarantor_name,
                'mobile': self.entry_id.legal_info.get('phone') if self.entry_id.is_self_guarantee else self.entry_id.guarantor_info.get('guarantor_phone'),
                'card_no': self.entry_id.legal_id_number if self.entry_id.is_self_guarantee else self.entry_id.guarantor_idcard_no,
                'sign_partner': 1,
            }),
            'template_id': t22_template.id,
        })

        self.entry_id.write({
            't18_contract_info_id': t18_contract.id,
            't22_contract_info_id': t22_contract.id
        })
        if self.entry_id.create_from == 'open_api':
            contract_info_ids = [t18_contract.id, t22_contract.id]
            entry_approval = self.env['ifs.gar.entry.merchant.approval.info.wizard'].sudo().create({
                'entry_id': self.entry_id.id,
                't18_contract_info_id': t18_contract.id,
                't22_contract_info_id': t22_contract.id
            })
            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, website_id=self.env.ref(
                    'website.default_website').id,
                sign_partner=self.entry_id,
                next_state='signed', ref_object=entry_approval)
                
            message_body = {
                'approval_info': {
                    'entry_code': self.entry_id.seq_code,
                    'state': 'approval',
                    'sign_url': sign_token.sign_url,
                    'empty_list': [],
                    'account_info': {
                        'approved_quota': int(self.entry_id.supplier_final_quota),
                        'credit_term': self.entry_id.credit_term,
                        'repay_day': self.entry_id.repay_day,
                        'financer_code': '',
                        'financer_name': '',
                    }
                }
            }
            self.entry_id.message_handler(message_body)
