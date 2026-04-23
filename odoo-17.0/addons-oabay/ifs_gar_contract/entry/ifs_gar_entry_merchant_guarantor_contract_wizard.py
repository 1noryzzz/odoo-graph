# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantGuarantorContractWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.guarantor.contract.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--担保人合同协议'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)

    guarantor_contract_info_id = fields.Many2one(
        'ifs.contract.info', related='entry_id.guarantor_contract_info_id', string='担保人征信查询授权书')
    guarantor_name = fields.Char('担保人姓名', related='entry_id.guarantor_name')

    guarantor_contract_name = fields.Char(
        '担保人征信查询授权书', related='guarantor_contract_info_id.name', readonly=True)
    guarantor_contract_pdf = fields.Binary(related='guarantor_contract_info_id.contract')
    guarantor_contract_state = fields.Selection(related='guarantor_contract_info_id.state')
    guarantor_contract_preview = fields.Binary(related='guarantor_contract_info_id.contract_preview')

    contract_state = fields.Boolean(
        "是否已提交签约", compute="_compute_contract_state")

    @api.depends('guarantor_contract_state')
    def _compute_contract_state(self):
        for contract in self:
            if contract.guarantor_contract_state in ['committed', 'signed']:
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
        pass

    def sign_contract(self):
        if self.user_has_groups('ifs_gar_invite.group_ifs_gar_merchant_entry'):
            contract_info_ids = []
            if self.guarantor_contract_info_id:
                contract_info_ids.append(self.guarantor_contract_info_id.id)

            sign_token = self.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, website_id=self.env.ref(
                    'website.default_website').id,
                sign_partner=self.entry_id,
                next_state='signed', ref_object=self.entry_id)

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
