# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied

copy_fields = ['ifs_risk_credits_id', 'guarantor_ifs_risk_credits_id', 'business_info_definition_id', 'legal_info_definition_id', 'legal_other_info_definition_id', 'guarantor_info_definition_id', 
               'current_model', 'phone', 'email', 'business_address', 'legal_name', 'legal_id_number', 'legal_nationality', 'legal_gender', 'legal_birthday', 'history_order_url',
               'legal_address', 'legal_authority', 'legal_start_date', 'legal_end_date', 'guarantor_name', 'guarantor_idcard_no', 'guarantor_nationality', 'guarantor_gender', 
               'guarantor_birthday', 'guarantor_address', 'guarantor_authority', 'guarantor_start_date', 'guarantor_end_date', 'business_info', 'legal_info', 'business_info_optional',
               'legal_other_info', 'guarantor_info', 'is_self_guarantee', 'f41_contract_info_id', 'f42_contract_info_id', 'f43_contract_info_id', 'business_info_optional_definition_id']


class GuaranteeAccountsRecReviewMerchantBtw(models.TransientModel):
    _name = 'ifs.gar.review.merchant.btw.wizard'
    _description = '驳回采购方进件'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', string='审批流程')
    btw_reason = fields.Html('驳回原因-详情', required=True)
    btw_reason_simple = fields.Char('驳回原因', required=True)

    def action_confirm(self):
        if self.entry_id:
            self.entry_id.write({
                'btw_reason': self.btw_reason,
                'btw_reason_simple': self.btw_reason_simple,
                'state': 'btw',
                'factor_approval_time': fields.Datetime.now(),
            })
            if self.entry_id.create_from == 'open_api':
                # new_entry = self.env['ifs.gar.entry.merchant'].sudo().create({
                #     'invite_id': self.entry_id.invite_id.id,
                #     'ifs_company_id': self.entry_id.ifs_company_id.id,
                #     'state': 'btw',
                #     'create_from': 'open_api',
                # })
                # new_record = {}
                # entry_fields = self.env['ifs.gar.entry.merchant'].fields_get()
                # # 遍历字段信息，将旧记录的字段值存储到新记录的字段值字典中
                # for field_name, field_info in entry_fields.items():
                #     if field_name in copy_fields:
                #         new_record[field_name] = self.entry_id[field_name]
                # new_entry.update(new_record)
                message_body = {
                    'approval_info': {
                        'entry_code': self.entry_id.seq_code,
                        'state': 'btw',
                        'hint': self.btw_reason_simple,
                        'empty_list': [],
                        'account_info': None
                    }
                }
                self.entry_id.message_handler(message_body)
        else:
            raise AccessDenied(_('无法找到审批流程'))
