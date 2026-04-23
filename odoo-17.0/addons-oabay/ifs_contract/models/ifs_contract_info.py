# -*- coding: utf-8 -*-

import base64
import fitz
import io
import logging
import PyPDF2

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError
from odoo.tools import safe_eval
from PyPDF2 import PdfFileReader
from PIL import Image

_logger = logging.getLogger(__name__)


class InclusiveFinancingContractInformation(models.Model):
    _name = 'ifs.contract.info'
    _description = '合同填充信息'
    _inherit = ['mail.render.mixin']
    _order = "create_date desc"
    _rec_name = 'name'

    name = fields.Char('名称', required=True, index=True)
    code = fields.Char(
        '合同编号', index=True, readonly=True, default=lambda self: _('New'))
    template_id = fields.Many2one(
        'ifs.contract.template', string='合同模板', required=True, index=True)
    need_partner = fields.Selection(related='template_id.need_partner')

    partner_one = fields.Reference(
        selection=[], string='甲方信息', ondelete='set null')
    partner_one_signature = fields.Image(
        '甲方签名', copy=False,
        attachment=True, max_width=1024, max_height=1024)
    partner_one_liveness_video = fields.Binary('甲方人脸核身视频')
    partner_one_best_frame = fields.Binary('甲方人脸核身截图')
    partner_two = fields.Reference(
        selection=[], string='乙方信息', ondelete='set null')
    partner_two_signature = fields.Image(
        '乙方签名', copy=False,
        attachment=True, max_width=1024, max_height=1024)
    partner_two_liveness_video = fields.Binary('乙方人脸核身视频')
    partner_two_best_frame = fields.Binary('乙方人脸核身截图')
    partner_three = fields.Reference(
        selection=[], string='丙方信息', ondelete='set null')
    partner_three_signature = fields.Image(
        '丙方签名', copy=False,
        attachment=True, max_width=1024, max_height=1024)
    partner_three_liveness_video = fields.Binary('丙方人脸核身视频')
    partner_three_best_frame = fields.Binary('丙方人脸核身截图')
    partner_four = fields.Reference(
        selection=[], string='丁方信息', ondelete='set null')
    partner_four_signature = fields.Image(
        '丁方签名', copy=False,
        attachment=True, max_width=1024, max_height=1024)
    partner_four_liveness_video = fields.Binary('丁方人脸核身视频')
    partner_four_best_frame = fields.Binary('丁方人脸核身截图')

    signer_name = fields.Char(
        "签约方", compute="_compute_signer_name", store=True)

    params = fields.Char(string='其它合同参数')

    report_content = fields.Html(
        '合同内容', compute='_compute_report_content',
        store=True, render_engine='qweb', translate=True, sanitize=False)
    template_content = fields.Html(
        '合同模板内容', store=True, render_engine='qweb', translate=True, sanitize=False)
    validity_period = fields.Integer(
        '合同有效期', required=True, default=24, help='合同签署后的有效时间，单位为月')

    token_ids = fields.Many2many(
        'ifs.contract.info.sign.token', 'ifs_contract_info_token_rel', 'contract_info_id', 'token_id', string='签名Token')

    state = fields.Selection([
        ('draft', '草稿'),
        ('unconfirmed', '待确认'),
        ('confirmed', '已确认'),
        ('committed', '已提交'),  # 已提交第三方存证
        ('signed', '已签署'),
        ('err', '签章错误'),
        ('abolished', '已作废'),
        ('expired', '已过期'),
    ], string='状态', default='draft')
    sign_date = fields.Date('签约日期')
    expire_date = fields.Date('合同到期时间')
    contract = fields.Binary('合同', copy=False)
    contract_preview = fields.Binary(
        '合同截图', compute='_compute_contract_preview', store=True, copy=False)

    @api.depends('contract')
    def _compute_contract_preview(self):
        desired_width = 300
        desired_height = 190
        for contract in self:
            try:
                if contract.contract:
                    with io.BytesIO(base64.b64decode(contract.contract)) as pdf_stream:
                        pdf_reader = PdfFileReader(pdf_stream)
                        if pdf_reader.numPages > 0:
                            first_page = pdf_reader.getPage(0)

                            # 计算截图的长宽
                            new_width = int(first_page.mediaBox[2])
                            new_height = int(
                                new_width / (desired_width / desired_height))

                            # 使用 PyMuPDF 将 PDF 页面转换为图像
                            doc = fitz.open(stream=pdf_stream, filetype="pdf")
                            pixmap = doc.load_page(0).get_pixmap()
                            pdf_image = Image.frombytes(
                                "RGB", (pixmap.width, pixmap.height), pixmap.samples)

                            # 调整图像大小并进行截图
                            pdf_image = pdf_image.crop(
                                (0, 0, new_width, new_height))
                            pdf_image = pdf_image.resize(
                                (desired_width * 2, desired_height * 2), Image.ANTIALIAS)

                            # 将图像保存为字节流
                            image_stream = io.BytesIO()
                            pdf_image.save(image_stream, format='JPEG')
                            image_stream.seek(0)

                            # 将字节流编码为 base64 字符串
                            encoded_image = base64.b64encode(
                                image_stream.read())

                            # 设置截图字段的值为编码后的图像数据
                            contract.contract_preview = encoded_image.decode()

                        # 关闭 PDF 文件
                        doc.close()
                else:
                    contract.contract_preview = False
            except PyPDF2.utils.PdfReadError:
                continue

    # Overrides of mail.render.mixin
    def _compute_render_model(self):
        for contract in self:
            contract.render_model = contract._name

    @api.depends(
        'template_id', 'partner_one', 'partner_one_signature',
        'partner_two', 'partner_two_signature',
        'partner_three', 'partner_three_signature',
        'partner_four', 'partner_four_signature', 'params', 'template_content')
    def _compute_report_content(self):
        for info in self:
            info.report_content = ''
            if info.template_id:
                info.report_content = info.generate_contract(
                    info.id, ['template_content', ]).get('template_content', '')

    @api.depends('expire_date')
    def _compute_contract_state(self):
        for contract in self:
            if contract.state == 'signed' and (contract.expire_date == True and contract.expire_date < fields.Date.context_today(self)):
                contract.state = 'expired'

    @api.depends(
        'partner_one', 'partner_two',
        'partner_three', 'partner_four')
    def _compute_signer_name(self):
        for contract in self:
            signer = []
            contract.signer_name = ''
            if contract.partner_one:
                signer.append(contract.partner_one.name)
            if contract.partner_two:
                signer.append(contract.partner_two.name)
            if contract.partner_three:
                signer.append(contract.partner_three.name)
            if contract.partner_four:
                signer.append(contract.partner_four.name)
            contract.signer_name = ','.join(signer)

    # @api.model
    # def _search_signer(self, operator, value):
    #     all_contract = self.env['ifs.contract.info'].search([])

    #     return [('id', "in", all_contract.filtered(
    #         lambda line: (
    #             line.partner_one and line.partner_one.name.find(value) != -1)
    #         or (
    #             line.partner_two and line.partner_two.name.find(value) != -1)
    #         or (
    #             line.partner_three and line.partner_three.name.find(value) != -1)
    #         or (
    #             line.partner_four and line.partner_four.name.find(value) != -1)
    #     ).ids)]

    def _task_compute_contract_state(self):
        for contract in self:
            if contract.expire_date:
                if contract.expire_date < fields.Date.context_today(self):
                    contract.state = 'expired'
                # TODO: 后续做扩展，通过得到的天数判断是否要发送短信通知
                # else:
                #     timedelta = contract.expire_date - fields.Date.context_today(self)
                #     #得到相差天数
                #     diff_day = timedelta.days
                #     print(diff_day)

    # TODO: 这里供合同签署的实现模块去扩展，以对接不同的第三方线上合同
    def _contract_sign(self, is_interactive=False):
        report = self.env['ir.actions.report']._get_report_from_name(
            "ifs_contract.print_contract")
        context = dict(self.env.context)
        data = {'context': context}
        pdf, _ = report.with_context(context)._render_qweb_pdf(
            report.report_name, self.id, data=data)

        contract_pdf = io.BytesIO(pdf)
        contract_pdf.name = ''.join([self.name, self.code, ".pdf"])
        if contract_pdf:
            self.state = 'signed'
            self.contract = base64.b64encode(contract_pdf.getvalue())
        else:
            raise UserError(_('签约失败！'))
        return contract_pdf

    def signature_all_by_interactive(self, business_type, sign_partner):
        self.signature_all()

    def signature_all(self):
        for contract in self:
            try:
                contract._contract_sign()
                # signed_file = contract._contract_sign()
                # if signed_file:
                #     contract.state = 'signed'
                #     contract.contract = base64.b64encode(
                #         signed_file.getvalue())
                # else:
                #     contract.state = 'err'
            except UserError as e:
                contract.state = 'err'
                raise e

    def refresh_contract(self, refresh_content=False):
        self.ensure_one()

        if self.state == 'signed':
            return

        if refresh_content:
            self._compute_report_content()

        self.signature_all()

    def is_need_faceid(self):
        need_faceid = False
        for contract in self:
            need_faceid = need_faceid or contract.template_id.need_faceid

        return need_faceid

    def is_need_sms_verify(self):
        need_sms_verify = False
        for contract in self:
            need_sms_verify = need_sms_verify or contract.template_id.need_sms_verify

        return need_sms_verify

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            template = self.env['ifs.contract.template'].browse(
                vals.get('template_id', 0))
            if not template.exists():
                raise ValidationError(_('您选择的模板不存在！'))

            vals.update({
                'template_content': template.body_html,
                'validity_period': template.validity_period,
            })
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'ifs.contract.info.%s' % template.code) or _('New')

        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals and vals.get('state', '') == 'signed':
            current_date = fields.Datetime.now()
            vals['sign_date'] = current_date
            vals['expire_date'] = current_date + \
                relativedelta(months=self.validity_period)

        return super().write(vals)

    def contract_view(self):
        self.ensure_one()

        return {
            'name': f'合同预览-{self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ifs.contract.info',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def generate_contract(self, res_ids, fields=['template_content']):
        """Generates an contract from the template for given the given model based on
        records given by res_ids.

        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        results = dict()
        for lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
            for field in fields:
                generated_field_values = template._render_field(
                    field, template_res_ids,
                    add_context={'json': safe_eval.json},
                    options={'post_process': (field == 'template_content')}
                )
                for res_id, field_value in generated_field_values.items():
                    results.setdefault(res_id, dict())[field] = field_value
            # update values for all res_ids
            # for res_id in template_res_ids:
            #     values = results[res_id]
            #     if values.get('body_html'):
            #         values['body'] = tools.html_sanitize(values['body_html'])

        return multi_mode and results or results[res_ids[0]]

    def commit_user_sign_contract(self):
        contract_nums = 0
        sign_tokens = self.env['ifs.contract.info.sign.token'].sudo().search(
            [('sync_state', '=', 'user_sign')])
        for sign_token in sign_tokens:
            for contract_info in sign_token.contract_info_ids:
                if contract_info.state == 'confirmed':
                    contract_nums += 1
                    try:
                        contract_info._contract_sign()
                    except UserError as e:
                        contract_info.state = 'err'

            sign_token.write({
                'sync_state': 'committed'
            })
        _logger.info(f"总共提交 {contract_nums} 条合同")
