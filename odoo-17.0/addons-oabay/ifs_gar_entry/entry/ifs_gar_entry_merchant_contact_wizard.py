# -*- coding: utf-8 -*-
import fitz
import PyPDF2
from PyPDF2 import PdfFileReader
from PIL import Image
import base64
import io

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError, UserError


class GuaranteeAccountsRecEntryMerchantContactWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.contact.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--联系人信息'
    _ref_model = 'ifs.gar.entry.merchant'

    def default_get(self, default_fields):
        defaults = super().default_get(default_fields)

        if 'entry_id' in default_fields:
            entry = self.env['ifs.gar.entry.merchant'].browse(
                defaults.get('entry_id'))
            cdetails = self.env['ifs.gar.entry.merchant.config'].retrieve_config(
                entry.factor_id.id, entry.supplier_id.id, ['FRXX', 'QTXGXX'])

            if cdetails and 'legal_info_definition_id' in default_fields:
                legal_cdetail = cdetails.filtered(lambda c: c.code == 'FRXX')
                if legal_cdetail.is_visible:
                    defaults.update({
                        'legal_info_config_detail_id': legal_cdetail.id,
                        'legal_info_definition_id': legal_cdetail.definition_id.id,
                        'legal_info_is_required': legal_cdetail.is_required,
                        'legal_info_visible': legal_cdetail.is_visible,
                    })
            if cdetails and 'other_info_definition_id' in default_fields:
                other_cdetail = cdetails.filtered(lambda c: c.code == 'QTXGXX')
                if other_cdetail.is_visible:
                    defaults.update({
                        'other_info_config_detail_id': other_cdetail.id,
                        'other_info_definition_id': other_cdetail.definition_id.id,
                        'other_info_is_required': other_cdetail.is_required,
                        'other_info_visible': other_cdetail.is_visible,
                    })

        return defaults

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)
    legal_front_image = fields.Image(string='身份证人像面', required=True)
    legal_back_image = fields.Image(string='身份证国徽面', required=True)
    legal_name = fields.Char('姓名')
    legal_id_number = fields.Char('身份证号')
    legal_nationality = fields.Char('民族')
    legal_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    legal_birthday = fields.Char('出生日期')
    legal_address = fields.Char('证件地址')
    legal_authority = fields.Char('签发机关')
    legal_start_date = fields.Char('起始日期')
    legal_end_date = fields.Char('失效日期')

    currency_id = fields.Many2one(
        'res.currency', string='Account Currency', related='entry_id.currency_id')
    is_has_legal_housing_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有房产', default='true')
    legal_housing_assets = fields.Monetary('现有价值')
    is_has_legal_vehicle_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='是否有汽车', default='true')
    legal_vehicle_assets = fields.Monetary('现有价值')
    is_has_legal_other_assets = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='其他固定财产', default='true')
    legal_other_assets_remarks = fields.Char('说明')
    legal_other_assets = fields.Monetary('现有价值')
    is_has_legal_loan = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有借款', default='true')
    legal_loan_remarks = fields.Char('说明')
    legal_loan_amount = fields.Monetary('金额')
    is_has_legal_guarantee = fields.Selection([
        ('true', '是'),
        ('false', '否')
    ], string='名下是否有担保', default='true')
    legal_guarantee_remarks = fields.Char('说明')
    legal_guarantee_amount = fields.Monetary('担保金额')

    legal_handle_image = fields.Binary('法人手持身份证照片', required=True)
    legal_person_property_certificate = fields.Binary(
        '法人名下相关财产证明')
    legal_person_property_certificate_preview = fields.Binary(
        '法人名下相关财产证明图片', compute='_compute_legal_person_property_certificate_preview', store=True)

    legal_info_config_detail_id = fields.Many2one(
        'ifs.gar.entry.merchant.config.detail', string='法人信息配置详情id')
    legal_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='法人信息配置id')
    legal_info_is_required = fields.Boolean('是否必填')
    legal_info_visible = fields.Boolean('是否可见')
    legal_info = fields.Properties(
        '法人信息', definition='legal_info_definition_id.params_definition')

    other_info_config_detail_id = fields.Many2one(
        'ifs.gar.entry.merchant.config.detail', string='紧急联系人配置详情id')
    other_info_definition_id = fields.Many2one(
        'ifs.gar.entry.definition', string='其他信息配置id')
    other_info_is_required = fields.Boolean('是否必填')
    other_info_visible = fields.Boolean('是否可见')
    other_info = fields.Properties(
        '其他信息', definition='other_info_definition_id.params_definition')

    @api.onchange('legal_front_image')
    def _onchange_front_image(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.legal_front_image:
            face_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.legal_front_image.decode('utf-8'),
                'configure': {'side': 'face'}
            }).retrieve_response('FACE')
            check_resp = ExternalApi.invoke(check_api_code, body={
                'id_number': face_resp.raw.get('num'),
                'name': face_resp.raw.get('name'),
            }).retrieve_response('CHECK')

            config = self.env['ir.config_parameter'].sudo()
            is_verification_name = config.get_param(
                'ifs.gar.entry.verification.legalperson.name')
            if is_verification_name and self.ifs_company_id.legal_id.name != face_resp.raw.get('name'):
                raise UserError(_("身份证信息和法人不一致"))

            if check_resp.raw.get('state'):
                self.update({
                    'legal_id_number': face_resp.raw.get('num'),
                    'legal_name': face_resp.raw.get('name'),
                    'legal_nationality': face_resp.raw.get('nationality'),
                    'legal_gender': face_resp.raw.get('sex'),
                    'legal_birthday': face_resp.raw.get('birth'),
                    'legal_address': face_resp.raw.get('address')
                })
        else:
            self.update({
                'legal_id_number': False,
                'legal_name': False,
                'legal_nationality': False,
                'legal_gender': False,
                'legal_birthday': False,
                'legal_address': False
            })

    @api.onchange('legal_back_image')
    def _onchange_back_image(self):
        Config = self.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        ExternalApi = self.env['galaxy.external.api'].sudo()

        if self.legal_back_image:
            back_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': self.legal_back_image.decode('utf-8'),
                'configure': {'side': 'back'}
            }).retrieve_response('BACK')
            self.update({
                'legal_authority': back_resp.raw.get('issue'),
                'legal_start_date': back_resp.raw.get('start_date'),
                'legal_end_date': back_resp.raw.get('end_date')
            })
        else:
            self.update({
                'legal_authority': False,
                'legal_start_date': False,
                'legal_end_date': False
            })

    def action_next(self):
        err_msgs = self.legal_info_config_detail_id.validate_required(
            self.legal_info) + self.other_info_config_detail_id.validate_required(self.other_info)
        if len(err_msgs) > 0:
            raise ValidationError(
                _(f'请填写法人相关信息！包含下列内容：\n\n{"，".join(err_msgs)}'))
        self.entry_id.write({
            'legal_front_image': self.legal_front_image,
            'legal_back_image': self.legal_back_image,
            'legal_name': self.legal_name,
            'legal_id_number': self.legal_id_number,
            'legal_nationality': self.legal_nationality,
            'legal_gender': self.legal_gender,
            'legal_birthday': self.legal_birthday,
            'legal_address': self.legal_address,
            'legal_authority': self.legal_authority,
            'legal_start_date': self.legal_start_date,
            'legal_end_date': self.legal_end_date,
            'legal_info_definition_id': self.legal_info_definition_id.id,
            'legal_info': self.legal_info if self.legal_info_visible else False,
            'is_has_legal_housing_assets': self.is_has_legal_housing_assets,
            'legal_housing_assets': self.legal_housing_assets,
            'is_has_legal_vehicle_assets': self.is_has_legal_vehicle_assets,
            'legal_vehicle_assets': self.legal_vehicle_assets,
            'is_has_legal_other_assets': self.is_has_legal_other_assets,
            'legal_other_assets_remarks': self.legal_other_assets_remarks,
            'legal_other_assets': self.legal_other_assets,
            'is_has_legal_loan': self.is_has_legal_loan,
            'legal_loan_remarks': self.legal_loan_remarks,
            'legal_loan_amount': self.legal_loan_amount,
            'is_has_legal_guarantee': self.is_has_legal_guarantee,
            'legal_guarantee_remarks': self.legal_guarantee_remarks,
            'legal_guarantee_amount': self.legal_guarantee_amount,
            'legal_other_info_definition_id': self.other_info_definition_id.id,
            'legal_other_info': self.other_info if self.other_info_visible else False,
            'legal_handle_image': self.legal_handle_image,
            'legal_person_property_certificate': self.legal_person_property_certificate,
            'legal_person_property_certificate_preview': self.legal_person_property_certificate_preview,
        })

        return super().action_next()

    @api.depends('legal_person_property_certificate')
    def _compute_legal_person_property_certificate_preview(self):
        desired_width = 300
        desired_height = 190
        for record in self:
            try:
                if record.legal_person_property_certificate:
                    with io.BytesIO(base64.b64decode(record.legal_person_property_certificate)) as pdf_stream:
                        pdf_reader = PdfFileReader(pdf_stream)
                        if pdf_reader.numPages > 0:
                            first_page = pdf_reader.getPage(0)

                            # 计算截图的长宽
                            new_width = int(first_page.mediaBox[2])
                            new_height = int(new_width / (desired_width / desired_height))

                            # 使用 PyMuPDF 将 PDF 页面转换为图像
                            doc = fitz.open(stream=pdf_stream, filetype="pdf")
                            pixmap = doc.load_page(0).get_pixmap()
                            pdf_image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

                            # 调整图像大小并进行截图
                            pdf_image = pdf_image.crop((0, 0, new_width, new_height))
                            pdf_image = pdf_image.resize((desired_width * 2, desired_height * 2), Image.ANTIALIAS)

                            # 将图像保存为字节流
                            image_stream = io.BytesIO()
                            pdf_image.save(image_stream, format='JPEG')
                            image_stream.seek(0)

                            # 将字节流编码为 base64 字符串
                            encoded_image = base64.b64encode(image_stream.read())

                            # 设置截图字段的值为编码后的图像数据
                            record.legal_person_property_certificate_preview = encoded_image.decode()

                        # 关闭 PDF 文件
                        doc.close()
                else:
                    record.legal_person_property_certificate_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
            