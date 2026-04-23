# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied
from datetime import datetime
from dateutil.relativedelta import relativedelta


class GuaranteeAccountsRecEntryMerchantApprWizard(models.TransientModel):
    _inherit = 'ifs.gar.entry.merchant.approval.info.wizard'
    _description = '采购方进件流程--签约'

    t18_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.t18_contract_info_id', string='最高子额度合同')
    t18_contract_name = fields.Char(
        '最高子额度合同', related='t18_contract_info_id.name')
    t18_contract_pdf = fields.Binary(related='t18_contract_info_id.contract')
    t18_contract_state = fields.Selection(related='t18_contract_info_id.state')
    t18_contract_preview = fields.Binary(related='t18_contract_info_id.contract_preview')

    t18a_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.t18a_contract_info_id', string='告知确认函')
    t18a_contract_name = fields.Char(
        '告知确认函', related='t18a_contract_info_id.name')
    t18a_contract_pdf = fields.Binary(related='t18a_contract_info_id.contract')
    t18a_contract_state = fields.Selection(related='t18a_contract_info_id.state')
    t18a_contract_preview = fields.Binary(related='t18a_contract_info_id.contract_preview')
    
    t22_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.t22_contract_info_id', string='最高额不可撤销担保书')
    t22_contract_name = fields.Char(
        '最高额不可撤销担保书', related='t22_contract_info_id.name')
    t22_contract_pdf = fields.Binary(related='t22_contract_info_id.contract')
    t22_contract_state = fields.Selection(related='t22_contract_info_id.state')
    t22_contract_preview = fields.Binary(related='t22_contract_info_id.contract_preview')

    contract_state = fields.Boolean(
        "是否已提交签约", compute="_compute_contract_state")

    @api.depends('t18_contract_state', 't22_contract_state')
    def _compute_contract_state(self):
        for contract in self:
            if contract.t18_contract_state in ['committed', 'signed'] and contract.t22_contract_state in ['committed', 'signed']:
                contract.contract_state = True
            else:
                contract.contract_state = False

    def preview_contract(self):
        contract_id = self.env.context.get('contract_id')
        contract_name = self.env.context.get('contract_name')
        return {
            'name': f'合同预览-{contract_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ifs.contract.info',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': contract_id,
        }

    def after_sign(self, next_state):
        # cron = self.env['ir.cron'].sudo().env.ref(
        #     'ifs_contract_sign_jzq.refresh_commit_contract_cron')
        # self.env['ir.cron.trigger'].sudo().create(
        #     {'cron_id': cron.id, 'call_at': datetime.now() + relativedelta(minute=5)}
        # )
        if self.entry_id.create_from == 'open_api':
            merchant = self.entry_id.confirm_merchant()

            merchant.payment_password = '123456'
            self.entry_id.write({
                'state': 'signed',
                'merchant_id': merchant.id
            })
            
            message_body = {
                'approval_info': {
                    'entry_code': self.entry_id.seq_code,
                    'merchant_code': merchant.seq_code,
                    'state': 'signed',
                    'empty_list': [],
                    'account_info': {
                        'approved_quota': int(self.entry_id.supplier_final_quota),
                        'credit_term': self.entry_id.credit_term,
                        'repay_day': self.entry_id.repay_day,
                        'financer_code': '',
                        'financer_name': '',
                    }
                },
            }
            self.entry_id.message_handler(message_body)

            change_password_temp_token = self.env['ifs.gar.change.password.temp.token'].sudo().create({
                'merchant_code': merchant.seq_code,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'next_name': _('设置支付密码'),
                    'next_url': f'/openapi/merchant/chpwd?token={change_password_temp_token.token}&merchant_code={change_password_temp_token.merchant_code}',
                    'next_description': _('开通成功，请设置支付密码！'),
                }
            }
            
        else:
            if self.t18_contract_state in ['committed', 'signed'] and self.t22_contract_state == 'draft' and not self.entry_id.is_self_guarantee:
                contract_info_ids = []
                contract_info_ids.append(self.t22_contract_info_id.id)
                sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                    contract_info_ids, website_id=self.env.ref(
                        'website.default_website').id,
                    sign_partner=self.entry_id, idcard=self.entry_id.guarantor_idcard_no,
                    next_state='signed', ref_object=self)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _(f'买方保证人签名成功，请连带责任保证人继续扫码签约！'),
                        'next': {
                            'name': _('请连带责任保证人使用手机扫码签约'),
                            'view_mode': 'form',
                            'view_type': 'form',
                            'views': [[self.env.ref('ifs_gar_contract.ifs_gar_contract_sign_wizard_view_form').id, 'form']],
                            'res_model': 'ifs.gar.contract.sign.wizard',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'context': {
                                'default_sign_token_id': sign_token.id,
                                'default_sign_url': sign_token.sign_url,
                            }
                        }
                    }
                }

    def sign_contract(self):
        if self.user_has_groups('ifs_gar_invite.group_ifs_gar_merchant_entry'):
            if not self.t18_contract_info_id:
                raise AccessDenied(_('没有最高子额度合同'))
            if not self.t22_contract_info_id:
                raise AccessDenied(_('没有最高额不可撤销担保书'))
            contract_info_ids = []
            if self.entry_id.is_self_guarantee:
                contract_info_ids.append(self.t18_contract_info_id.id)
                contract_info_ids.append(self.t22_contract_info_id.id)
                # if self.t18a_contract_info_id:
                #     contract_info_ids.append(self.t18a_contract_info_id.id)

                sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                    contract_info_ids, website_id=self.env.ref(
                        'website.default_website').id,
                    sign_partner=self.entry_id, idcard=self.entry_id.legal_id_number,
                    next_state='signed', ref_object=self)
            else:
                contract_info_ids.append(self.t18_contract_info_id.id)
                sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                    contract_info_ids, website_id=self.env.ref(
                        'website.default_website').id,
                    sign_partner=self.entry_id, idcard=self.entry_id.legal_id_number,
                    next_state='signed', ref_object=self)

            return {
                'name': _('请使用手机扫码签约'),
                'view_mode': 'form',
                'view_type': 'form',
                'views': [[self.env.ref('ifs_gar_contract.ifs_gar_contract_sign_wizard_view_form').id, 'form']],
                'res_model': 'ifs.gar.contract.sign.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_sign_token_id': sign_token.id,
                    'default_sign_url': sign_token.sign_url,
                }
            }
