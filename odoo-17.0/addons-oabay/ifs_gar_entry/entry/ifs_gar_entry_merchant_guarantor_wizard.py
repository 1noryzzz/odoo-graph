# -*- coding: utf-8 -*-
import json

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class GuaranteeAccountsRecEntryMerchantGuarantorWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.guarantor.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--担保人告知信息'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)

    clause_one_is_agree = fields.Boolean('告知信息1', required=True)
    clause_two_is_agree = fields.Boolean('告知信息1', required=True)
    clause_three_is_agree = fields.Boolean('告知信息1', required=True)
    is_self_guarantee = fields.Boolean('是否自我担保', required=True)

    def step_info(self, entry_id):
        step = self.search([('entry_id', '=', entry_id)], limit=1)
        if step.id and not step.is_self_guarantee:
            next_model = 'ifs.gar.entry.merchant.guarantor.wizard.info'
            return (self.env[next_model].search([('entry_id', '=', entry_id)]).id, next_model)
        return (step.id, self._name)

    def action_guarantor_info(self):
        if self.clause_one_is_agree and self.clause_two_is_agree and self.clause_three_is_agree:
            self.entry_id.write({
                'is_self_guarantee': self.is_self_guarantee,
            })
            if self.is_self_guarantee:
                return self.entry_id.action_next()
            else:
                return self.entry_id.nosave_refresh()
        else:
            raise ValidationError(_('请仔细阅读告知信息并勾选同意后再进行下一步操作'))


class GuaranteeAccountsRecEntryMerchantGuarantorWizardInfo(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.guarantor.wizard.info'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--担保人信息'
    _ref_model = 'ifs.gar.entry.merchant'

    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)

        if 'entry_id' in default_fields:
            entry = self.env['ifs.gar.entry.merchant'].browse(
                defaults.get('entry_id'))

            if 'guarantor_info_config_detail_id' in default_fields:
                cdetails = self.env['ifs.gar.entry.merchant.config'].retrieve_config(
                    entry.factor_id.id, entry.supplier_id.id, ['DBRXX'])

                cdetail = cdetails.filtered(lambda c: c.code == 'DBRXX')
                if cdetail.is_visible:
                    defaults.update({
                        'guarantor_info_config_detail_id': cdetail.id,
                        'guarantor_info_definition_id': cdetail.definition_id.id,
                        'guarantor_info_is_required': cdetail.is_required,
                        'guarantor_info_is_visible': cdetail.is_visible,
                    })

        return defaults

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    is_self_guarantee = fields.Boolean('是否自我担保', default=False)
    guarantor_front_image = fields.Image('身份证人像面', required=True)
    guarantor_back_image = fields.Image('身份证国徽面', required=True)
    guarantor_name = fields.Char('姓名')
    guarantor_idcard_no = fields.Char('身份证号')
    guarantor_nationality = fields.Char('民族')
    guarantor_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    guarantor_birthday = fields.Char('出生日期')
    guarantor_address = fields.Char('证件地址')
    guarantor_authority = fields.Char('签发机关')
    guarantor_start_date = fields.Char('起始日期')
    guarantor_end_date = fields.Char('失效日期')

    currency_id = fields.Many2one(
        'res.currency', string='Account Currency', related='entry_id.currency_id')
    is_has_guarantor_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产', default='true')
    guarantor_housing_assets = fields.Monetary('现有价值')
    is_has_guarantor_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有汽车', default='true')
    guarantor_vehicle_assets = fields.Monetary('现有价值')
    is_has_guarantor_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定财产', default='true')
    guarantor_other_assets_remarks = fields.Char('说明')
    guarantor_other_assets = fields.Monetary('现有价值')
    is_has_guarantor_loan = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有借款', default='true')
    guarantor_loan_remarks = fields.Char('说明')
    guarantor_loan_amount = fields.Monetary('金额')
    is_has_guarantor_guarantee = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有担保', default='true')
    guarantor_guarantee_remarks = fields.Char('说明')
    guarantor_guarantee_amount = fields.Monetary('担保金额')

    guarantor_info_config_detail_id = fields.Many2one(
        'ifs.gar.entry.merchant.config.detail', string='担保人信息配置详情id')
    guarantor_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='担保人信息配置id')
    guarantor_info_is_required = fields.Boolean('是否必填')
    guarantor_info_is_visible = fields.Boolean('是否可见')
    guarantor_info = fields.Properties(
        '担保人信息', definition='guarantor_info_definition_id.params_definition')

    @api.onchange('guarantor_front_image')
    def _onchange_front_image(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.guarantor_front_image:
            face_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.guarantor_front_image.decode('utf-8'),
                'configure': {'side': 'face'}
            }).retrieve_response('FACE')

            check_resp = ExternalApi.invoke(check_api_code, body={
                'id_number': face_resp.raw.get('num'),
                'name': face_resp.raw.get('name'),
            }).retrieve_response('CHECK')
            if check_resp.raw.get('state'):
                self.update({
                    'guarantor_name': face_resp.raw.get('name'),
                    'guarantor_idcard_no': face_resp.raw.get('num'),
                    'guarantor_nationality': face_resp.raw.get('nationality'),
                    'guarantor_gender': face_resp.raw.get('sex'),
                    'guarantor_birthday': face_resp.raw.get('birth'),
                    'guarantor_address': face_resp.raw.get('address'),
                    'is_self_guarantee': self.ifs_company_id.legal_id.name == face_resp.raw.get('name')
                })
        else:
            self.update({
                'guarantor_name': False,
                'guarantor_idcard_no': False,
                'guarantor_nationality': False,
                'guarantor_gender': False,
                'guarantor_birthday': False,
                'guarantor_address': False,
                'is_self_guarantee': False,
            })

    @api.onchange('guarantor_back_image')
    def _onchange_back_image(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.guarantor_back_image:
            back_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.guarantor_back_image.decode('utf-8'),
                'configure': {'side': 'back'}
            }).retrieve_response('BACK')

            self.update({
                'guarantor_authority': back_resp.raw.get('issue'),
                'guarantor_start_date': back_resp.raw.get('start_date'),
                'guarantor_end_date': back_resp.raw.get('end_date'),
            })
        else:
            self.update({
                'guarantor_authority': False,
                'guarantor_start_date': False,
                'guarantor_end_date': False,
            })

    def action_next(self):
        err_msgs = self.guarantor_info_config_detail_id.validate_required(
            self.guarantor_info)
        if len(err_msgs) > 0:
            raise ValidationError(
                _(f'请填写担保人相关信息！包含下列内容：\n\n{"，".join(err_msgs)}'))
            
        guarantor_template = self.env['ifs.contract.template'].retrieve_by_code(
            'F41', self.entry_id.invite_id.factor_id.id, self.entry_id.invite_id.supplier_id.id)
        guarantor_contract = self.env['ifs.contract.info'].create({
            'name': guarantor_template.name,
            'template_id': guarantor_template.id,
            'partner_one': '%s,%d' % (self.entry_id._name, self.entry_id.id),
            'params': json.dumps({
                'name': self.guarantor_name,
                'id_number': self.guarantor_idcard_no,
            }),
        })

        self.entry_id.write({
            'guarantor_front_image': self.guarantor_front_image,
            'guarantor_back_image': self.guarantor_back_image,
            'guarantor_name': self.guarantor_name,
            'guarantor_idcard_no': self.guarantor_idcard_no,
            'guarantor_nationality': self.guarantor_nationality,
            'guarantor_gender': self.guarantor_gender,
            'guarantor_birthday': self.guarantor_birthday,
            'guarantor_address': self.guarantor_address,
            'guarantor_authority': self.guarantor_authority,
            'guarantor_start_date': self.guarantor_start_date,
            'guarantor_end_date': self.guarantor_end_date,
            'guarantor_info_definition_id': self.guarantor_info_definition_id.id,
            'guarantor_info': self.guarantor_info if self.guarantor_info_is_visible else False,
            'is_has_guarantor_housing_assets': self.is_has_guarantor_housing_assets,
            'guarantor_housing_assets': self.guarantor_housing_assets,
            'is_has_guarantor_vehicle_assets': self.is_has_guarantor_vehicle_assets,
            'guarantor_vehicle_assets': self.guarantor_vehicle_assets,
            'is_has_guarantor_other_assets': self.is_has_guarantor_other_assets,
            'guarantor_other_assets_remarks': self.guarantor_other_assets_remarks,
            'guarantor_other_assets': self.guarantor_other_assets,
            'is_has_guarantor_loan': self.is_has_guarantor_loan,
            'guarantor_loan_remarks': self.guarantor_loan_remarks,
            'guarantor_loan_amount': self.guarantor_loan_amount,
            'is_has_guarantor_guarantee': self.is_has_guarantor_guarantee,
            'guarantor_guarantee_remarks': self.guarantor_guarantee_remarks,
            'guarantor_guarantee_amount': self.guarantor_guarantee_amount,
            'is_self_guarantee': self.is_self_guarantee,
            'guarantor_contract_info_id': guarantor_contract.id
        })

        return super().action_next()
