# -*- coding: utf-8 -*-
import json

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GuaranteeAccountsRecEntryMerchant(models.Model):
    _inherit = 'ifs.gar.entry.merchant'

    def _step_models(self):
        return [
            'ifs.gar.entry.merchant.cover.wizard',
            'ifs.gar.entry.merchant.base.info.wizard',
            'ifs.gar.entry.merchant.contact.wizard',
            'ifs.gar.entry.merchant.guarantor.wizard',
            'ifs.gar.entry.merchant.doc.wizard',
            'ifs.gar.entry.merchant.contract.wizard',
            'ifs.gar.entry.merchant.finish.wizard',
        ]

    t18_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='最高子额度合同')
    t18a_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='告知确认函')
    t22_contract_info_id = fields.Many2one(
        'ifs.contract.info', string='最高额不可撤销担保书')
    f41_contract_info_id = fields.Many2one(
        'ifs.contract.info', string="征信查询授权书")
    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', string="数字证书托管协议")
    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', string="CMCA数字证书订户协议")
    guarantor_contract_info_id = fields.Many2one(
        'ifs.contract.info', string="担保人征信查询授权书")

    t18_contract_name = fields.Char(
        '最高子额度合同', related='t18_contract_info_id.name', readonly=True)
    t18_contract_state = fields.Selection(related='t18_contract_info_id.state')
    t18_contract_pdf = fields.Binary(related='t18_contract_info_id.contract')
    t18_contract_preview = fields.Binary(related='t18_contract_info_id.contract_preview')

    t18a_contract_name = fields.Char(
        '告知确认函', related='t18a_contract_info_id.name', readonly=True)
    t18a_contract_state = fields.Selection(related='t18a_contract_info_id.state')
    t18a_contract_pdf = fields.Binary(related='t18a_contract_info_id.contract')
    t18a_contract_preview = fields.Binary(related='t18a_contract_info_id.contract_preview')
    
    t22_contract_name = fields.Char(
        '最高额不可撤销担保书', related='t22_contract_info_id.name', readonly=True)
    t22_contract_state = fields.Selection(related='t22_contract_info_id.state')
    t22_contract_pdf = fields.Binary(related='t22_contract_info_id.contract')
    t22_contract_preview = fields.Binary(related='t22_contract_info_id.contract_preview')

    f41_contract_name = fields.Char(
        '征信查询授权书', related='f41_contract_info_id.name', readonly=True)
    f41_contract_pdf = fields.Binary(related='f41_contract_info_id.contract')
    f41_contract_state = fields.Selection(related='f41_contract_info_id.state')
    f41_contract_preview = fields.Binary(related='f41_contract_info_id.contract_preview')

    f42_contract_name = fields.Char(
        '数字证书托管', related='f42_contract_info_id.name', readonly=True)
    f42_contract_pdf = fields.Binary(related='f42_contract_info_id.contract')
    f42_contract_state = fields.Selection(related='f42_contract_info_id.state')
    f42_contract_preview = fields.Binary(related='f42_contract_info_id.contract_preview')

    f43_contract_name = fields.Char(
        '数字证书申请', related='f43_contract_info_id.name', readonly=True)
    f43_contract_pdf = fields.Binary(related='f43_contract_info_id.contract')
    f43_contract_state = fields.Selection(related='f43_contract_info_id.state')
    f43_contract_preview = fields.Binary(related='f43_contract_info_id.contract_preview')
    
    guarantor_contract_name = fields.Char(
        '担保人征信查询授权书', related='guarantor_contract_info_id.name', readonly=True)
    guarantor_contract_pdf = fields.Binary(related='guarantor_contract_info_id.contract')
    guarantor_contract_state = fields.Selection(related='guarantor_contract_info_id.state')
    guarantor_contract_preview = fields.Binary(related='guarantor_contract_info_id.contract_preview')

    @api.model_create_multi
    def create(self, vals_list):
        entry_list = super().create(vals_list)
        for entry_id in entry_list:
            f41_template = self.env['ifs.contract.template'].retrieve_by_code(
                'F41', entry_id.invite_id.factor_id.id, entry_id.invite_id.supplier_id.id)
            f42_template = self.env['ifs.contract.template'].retrieve_by_code(
                'F42', entry_id.invite_id.factor_id.id, entry_id.invite_id.supplier_id.id)
            f43_template = self.env['ifs.contract.template'].retrieve_by_code(
                'F43', entry_id.invite_id.factor_id.id, entry_id.invite_id.supplier_id.id)

            f41_contract = self.env['ifs.contract.info'].create({
                'name': f41_template.name,
                'template_id': f41_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id),
                'params': json.dumps({
                    'name': self.legal_id.name
                }),
            })
            f42_contract = self.env['ifs.contract.info'].create({
                'name': f42_template.name,
                'template_id': f42_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id)
            })
            f43_contract = self.env['ifs.contract.info'].create({
                'name': f43_template.name,
                'template_id': f43_template.id,
                'partner_one': '%s,%d' % (entry_id._name, entry_id.id)
            })

            entry_id.write({
                'f41_contract_info_id': f41_contract.id,
                'f42_contract_info_id': f42_contract.id,
                'f43_contract_info_id': f43_contract.id
            })
        return entry_list

    def write(self, vals):
        res = super().write(vals)
        if 'email' in vals or 'phone' in vals:
            self.f43_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
        elif 'legal_id_number' in vals or 'guarantor_idcard_no' in vals:
            self.f41_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
                'params': json.dumps({
                    'name': self.legal_name if self.is_self_guarantee else self.guarantor_name,
                    'id_number': self.legal_id_number if self.is_self_guarantee else self.guarantor_idcard_no,
                }),
            })
            self.f42_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })
            self.f43_contract_info_id.write({
                'partner_one': '%s,%d' % (self._name, self.id),
            })

        return res

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

    def after_sign(self, sign_token):
        super().after_sign(sign_token)

        for record in self:
            if record.create_from == 'open_api' and record.state == 'committed':
                is_sign = record.f41_contract_state in ['committed', 'signed'] and record.f42_contract_state in [
                    'committed', 'signed'] and record.f43_contract_state in ['committed', 'signed']
                if is_sign:
                    list_type = record.business_info.get('list_type')
                    if list_type in [10, 30]:
                        record.write({
                            'state': 'approve' if list_type == 10 else 'btw',
                            'factor_approval_time': fields.Datetime.now()
                        })

                        message_body = {
                            'approval_info': {
                                'entry_code': record.seq_code,
                                'state': record.state,
                                'hint': record.business_info.get('list_reason') if list_type == 30 else None,
                                'empty_list': [],
                                'account_info': None
                            }
                        }

                        # 推送状态通知
                        api_app = self.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{record.supplier_id.id}')], order='create_date desc', limit=1)
                        if not api_app:
                            raise UserError(_('没有找到对应的应用！'))
                        self.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)

    def confirm_merchant(self):
        merchant = super().confirm_merchant()

        factor_merchant = self.env['ifs.gar.partner.factor.merchant'].sudo().search([
            ('factor_id', '=', self.factor_id.id),
            ('merchant_id', '=', merchant.id),
        ], limit=1)
        supplier_merchant = self.env['ifs.gar.partner.supplier.merchant'].sudo().search([
            ('factor_supplier_id.supplier_id', '=', self.supplier_id.id),
            ('merchant_id', '=', merchant.id),
        ], limit=1)

        factor_merchant.write({
            'f41_contract_info_id': self.f41_contract_info_id.id,
            'f42_contract_info_id': self.f42_contract_info_id.id,
            'f43_contract_info_id': self.f43_contract_info_id.id,
        })
        supplier_merchant.write({
            't18_contract_info_id': self.t18_contract_info_id.id,
            # 't18a_contract_info_id': self.t18a_contract_info_id.id,
            't22_contract_info_id': self.t22_contract_info_id.id,
        })

        return merchant
