# -*- coding: utf-8 -*-
import fitz
import PyPDF2
from PyPDF2 import PdfFileReader
from PIL import Image
import base64
import io

from odoo import _, api, models, fields


class GuaranteeAccountsRecEntryMerchantDocWizard(models.TransientModel):
    _name = 'ifs.gar.entry.merchant.doc.wizard'
    _inherit = ['ifs.gar.entry.step']
    _description = '采购方进件流程--附件信息'
    _ref_model = 'ifs.gar.entry.merchant'

    entry_id = fields.Many2one(
        'ifs.gar.entry.merchant', required=True, ondelete='restrict', index=True)

    reception_picture = fields.Binary('前台照', required=True)
    office_area_picture = fields.Binary('公司办公区照片', required=True)
    charter = fields.Binary('公司章程', required=True)
    charter_preview = fields.Binary('公司章程', compute='_compute_charter_preview', store=True)
    lease_contract = fields.Binary('租赁合同', required=True)
    lease_contract_preview = fields.Binary('租赁合同', compute='_compute_lease_contract_preview', store=True)
    half_year_balance_sheet = fields.Binary('近半年的资产负债表', required=True)
    half_year_balance_sheet_preview = fields.Binary('近半年的资产负债表', compute='_compute_half_year_balance_sheet_preview', store=True)
    half_year_cash_flow_sheet = fields.Binary('近半年现金流量表', required=True)
    half_year_cash_flow_sheet_preview = fields.Binary('近半年现金流量表', compute='_compute_half_year_cash_flow_sheet_preview', store=True)
    half_year_assets_gains_losses_sheet = fields.Binary('近半年资产损益表', required=True)
    half_year_assets_gains_losses_sheet_preview = fields.Binary('近半年资产损益表', compute='_compute_half_year_assets_gains_losses_sheet_preview', store=True)
    enterprise_property_certificate = fields.Binary('企业名下相关财产证明')
    enterprise_property_certificate_preview = fields.Binary('企业名下相关财产证明', compute='_compute_enterprise_property_certificate_preview', store=True)

    def action_next(self):
        self.entry_id.write({
            'reception_picture': self.reception_picture,
            'office_area_picture': self.office_area_picture,
            'charter': self.charter,
            'charter_preview': self.charter_preview,
            'lease_contract': self.lease_contract,
            'lease_contract_preview': self.lease_contract_preview,
            'half_year_balance_sheet': self.half_year_balance_sheet,
            'half_year_balance_sheet_preview': self.half_year_balance_sheet_preview,
            'half_year_cash_flow_sheet': self.half_year_cash_flow_sheet,
            'half_year_cash_flow_sheet_preview': self.half_year_cash_flow_sheet_preview,
            'half_year_assets_gains_losses_sheet': self.half_year_assets_gains_losses_sheet,
            'half_year_assets_gains_losses_sheet_preview': self.half_year_assets_gains_losses_sheet_preview,
            'enterprise_property_certificate': self.enterprise_property_certificate,
            'enterprise_property_certificate_preview': self.enterprise_property_certificate_preview,
        })

        return super().action_next()
    
    def _intercept_preview(self, data):
        desired_width = 300
        desired_height = 190
        preview_data = False
        with io.BytesIO(base64.b64decode(data)) as pdf_stream:
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
                preview_data = encoded_image.decode()

            # 关闭 PDF 文件
            doc.close()
            return preview_data
    
    @api.depends('charter')
    def _compute_charter_preview(self):
        for record in self:
            try:
                if record.charter:
                    record.charter_preview = self._intercept_preview(record.charter)
                else:
                    record.charter_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
                
    @api.depends('lease_contract')
    def _compute_lease_contract_preview(self):
        for record in self:
            try:
                if record.lease_contract:
                    record.lease_contract_preview = self._intercept_preview(record.lease_contract)
                else:
                    record.lease_contract_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
                
    @api.depends('half_year_balance_sheet')
    def _compute_half_year_balance_sheet_preview(self):
        for record in self:
            try:
                if record.half_year_balance_sheet:
                    record.half_year_balance_sheet_preview = self._intercept_preview(record.half_year_balance_sheet)
                else:
                    record.half_year_balance_sheet_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
                
    @api.depends('half_year_cash_flow_sheet')
    def _compute_half_year_cash_flow_sheet_preview(self):
        for record in self:
            try:
                if record.half_year_cash_flow_sheet:
                    record.half_year_cash_flow_sheet_preview = self._intercept_preview(record.half_year_cash_flow_sheet)
                else:
                    record.half_year_cash_flow_sheet_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
                
    @api.depends('half_year_assets_gains_losses_sheet')
    def _compute_half_year_assets_gains_losses_sheet_preview(self):
        for record in self:
            try:
                if record.half_year_assets_gains_losses_sheet:
                    record.half_year_assets_gains_losses_sheet_preview = self._intercept_preview(record.half_year_assets_gains_losses_sheet)
                else:
                    record.half_year_assets_gains_losses_sheet_preview = False
            except PyPDF2.utils.PdfReadError:
                continue
                
    @api.depends('enterprise_property_certificate')
    def _compute_enterprise_property_certificate_preview(self):
        for record in self:
            try:
                if record.enterprise_property_certificate:
                    record.enterprise_property_certificate_preview = self._intercept_preview(record.enterprise_property_certificate)
                else:
                    record.enterprise_property_certificate_preview = False  
            except PyPDF2.utils.PdfReadError:
                continue          