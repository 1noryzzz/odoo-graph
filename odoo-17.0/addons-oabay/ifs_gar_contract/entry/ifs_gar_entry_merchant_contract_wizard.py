# -*- coding: utf-8 -*-


from odoo import _, api, models, fields
from datetime import datetime
from dateutil.relativedelta import relativedelta


class GuaranteeAccountsRecEntryMerchantContractWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.contract.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--合同协议'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)

    f41_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.f41_contract_info_id', string='征信查询授权书')
    f42_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.f42_contract_info_id', string='数字证书托管协议')
    f43_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.f43_contract_info_id', string='CMCA数字证书订户协议')

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

    contract_state = fields.Boolean(
        "是否已提交签约", compute="_compute_contract_state")

    @api.depends('f41_contract_state', 'f42_contract_state', 'f43_contract_state')
    def _compute_contract_state(self):
        for contract in self:
            if contract.f41_contract_state in ['committed', 'signed'] and contract.f42_contract_state in ['committed', 'signed'] and contract.f43_contract_state in ['committed', 'signed']:
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

    def after_sign(self, sign_token):
        # cron = self.env['ir.cron'].sudo().env.ref(
        #     'ifs_contract_sign_jzq.refresh_commit_contract_cron')
        # self.env['ir.cron.trigger'].sudo().create(
        #     {'cron_id': cron.id, 'call_at': datetime.now() + relativedelta(minute=5)}
        # )
        pass

    def sign_contract(self):
        if self.user_has_groups('ifs_gar_invite.group_ifs_gar_merchant_entry'):
            contract_info_ids = []
            if self.f41_contract_info_id:
                contract_info_ids.append(self.f41_contract_info_id.id)
            if self.f42_contract_info_id:
                contract_info_ids.append(self.f42_contract_info_id.id)
            if self.f43_contract_info_id:
                contract_info_ids.append(self.f43_contract_info_id.id)

            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, website_id=self.env.ref(
                    'website.default_website').id,
                sign_partner=self.entry_id,
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
            
    def step_info(self, entry_id):
        step = self.search([('entry_id', '=', entry_id)], limit=1)
        if step.id and not step.entry_id.is_self_guarantee:
            next_model = 'ifs.gar.entry.merchant.guarantor.contract.wizard'
            return (self.env[next_model].search([('entry_id', '=', entry_id)]).id, next_model)
        return (step.id, self._name)
            
    def action_next(self):
        if self.entry_id.is_self_guarantee:
            return self.entry_id.action_next()
        else:
            return self.entry_id.nosave_refresh()
