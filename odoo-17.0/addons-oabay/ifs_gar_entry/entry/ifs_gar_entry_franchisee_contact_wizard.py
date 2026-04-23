# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GuaranteeAccountsRecEntryFranchiseeContactWizard(models.TransientModel):
    _name = 'ifs.gar.entry.franchisee.contact.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '合伙人进件流程--联系人信息'
    _ref_model = 'ifs.gar.entry.franchisee'

    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', required=True, ondelete='restrict', index=True)

    contact_front_image = fields.Image(
        string='身份证人像面', required=True, prefetch=True)
    contact_back_image = fields.Image(
        string='身份证国徽面', required=True, prefetch=True)
    contact_name = fields.Char('姓名', required=True)
    contact_id_number = fields.Char('身份证号', required=True)
    contact_nationality = fields.Char('民族')
    contact_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    contact_birthday = fields.Char('出生日期')
    contact_address = fields.Char('证件地址', required=True)
    contact_authority = fields.Char('签发机关', required=True)
    contact_start_date = fields.Char('起始日期', required=True)
    contact_end_date = fields.Char('失效日期')

    @api.onchange('contact_front_image')
    def _onchange_contact_front_image(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.contact_front_image:
            face_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.contact_front_image.decode('utf-8'),
                'configure': {'side': 'face'}
            }).retrieve_response('FACE')
            check_resp = ExternalApi.invoke(check_api_code, body={
                'id_number': face_resp.raw.get('num'),
                'name': face_resp.raw.get('name'),
            }).retrieve_response('CHECK')

            config = self.env['ir.config_parameter'].sudo()
            is_verification_name = config.get_param('ifs.gar.entry.verification.legalperson.name')
            if is_verification_name and self.ifs_company_id.legal_id.name != face_resp.raw.get('name'):
                raise UserError(_("身份证信息和法人不一致"))

            if check_resp.raw.get('state'):
                self.update({
                    'contact_name': face_resp.raw.get('name'),
                    'contact_id_number': face_resp.raw.get('num'),
                    'contact_nationality': face_resp.raw.get('nationality'),
                    'contact_gender': face_resp.raw.get('sex'),
                    'contact_birthday': face_resp.raw.get('birth'),
                    'contact_address': face_resp.raw.get('address'),
                })
        else:
            self.update({
                'contact_name': False,
                'contact_id_number': False,
                'contact_nationality': False,
                'contact_gender': False,
                'contact_birthday': False,
                'contact_address': False,
            })

    @api.onchange('contact_back_image')
    def _onchange_idcard_info(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.contact_back_image:
            back_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.contact_back_image.decode('utf-8'),
                'configure': {'side': 'back'}
            }).retrieve_response('BACK')
            self.update({
                'contact_authority': back_resp.raw.get('issue'),
                'contact_start_date': back_resp.raw.get('start_date'),
                'contact_end_date': back_resp.raw.get('end_date'),
            })
        else:
            self.update({
                'contact_authority': False,
                'contact_start_date': False,
                'contact_end_date': False,
            })

    def action_next(self):
        self.entry_id.write({
            'legal_front_image': self.contact_front_image,
            'legal_back_image': self.contact_back_image,
            'legal_name': self.contact_name,
            'legal_id_number': self.contact_id_number,
            'legal_nationality': self.contact_nationality,
            'legal_gender': self.contact_gender,
            'legal_birthday': self.contact_birthday,
            'legal_address': self.contact_address,
            'legal_authority': self.contact_authority,
            'legal_start_date': self.contact_start_date,
            'legal_end_date': self.contact_end_date,
        })

        return super().action_next()
