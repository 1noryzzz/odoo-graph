# -*- coding: utf-8 -*-

import logging
import base64

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)

VALIDITY_PERIOD = [
    ('0.5', '半年'),
    ('1.0', '一年'),
    ('2.0', '两年'),
    ('3.0', '三年'),
    ('5.0', '五年'),
    ('8.0', '八年'),
    ('10.0', '十年')
]


class InclusiveFinancingContractTemplate(models.Model):
    _name = 'ifs.contract.template'
    _description = '合同模板'
    _inherit = ['mail.render.mixin']
    _order = 'code'
    _unrestricted_rendering = True

    _sql_constraints = [
        ('code_uniq', 'unique (code)', '合同模板编号已存在！')
    ]

    @api.model
    def default_get(self, fields):
        res = super(InclusiveFinancingContractTemplate,
                    self).default_get(fields)
        if self.user_has_groups('base.group_system'):
            if res.get('model'):
                res['model_id'] = self.env['ir.model']._get(
                    res.pop('model')).id
            else:
                model = self.env['ir.model'].search(
                    [('model', '=', 'ifs.contract.info')])
                if model.exists():
                    res.update({
                        'model_id': model.id,
                        'model': model.model,
                    })
        return res

    name = fields.Char('名称', required=True)
    code = fields.Char('合同模板编号', required=True, help="合同模板被引用时的唯一编号")
    need_partner = fields.Selection([
        ('one', '单方面'),
        ('two', '甲乙双方'),
        ('three', '三方合同'),
        ('four', '四方合同'),
    ], string='合同参与方', default='one')
    need_faceid = fields.Boolean('人脸核身', default=True)
    need_sms_verify = fields.Boolean('短信验证', default=False)
    sign_position_params = fields.Char('签约位置参数设置')
    validity_period = fields.Integer(
        '合同有效期', required=True, default=24, help='合同签署后的有效时间，单位为月')
    validity_period_sel = fields.Selection(
        VALIDITY_PERIOD, string='合同有效期', compute='_compute_validity_period', readonly=False)
    validity_period_view = fields.Char(
        '合同有效期', compute='_compute_validity_period')
    model_id = fields.Many2one(
        'ir.model', '应用于', help="The type of document this template can be used with")
    model = fields.Char(
        '内容来源于', related='model_id.model', index=True, store=True, readonly=True)
    body_html = fields.Html(
        '合同内容', render_engine='qweb', translate=True, sanitize=False)
    category_id = fields.Many2one('ifs.contract.category', string='合同分类')

    report_name = fields.Char(
        '合同输出名称', translate=True,
        help="Name to use for the generated report file (may contain placeholders)\n"
        "The extension can be omitted and will then come from the report type.")
    report_template = fields.Many2one(
        'ir.actions.report', 'Optional report to print and attach')

    ref_ir_act_window = fields.Many2one(
        'ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
        help="Sidebar action to make this template available on records "
        "of the related document model")
    tag_ids = fields.Many2many(
        'ifs.contract.tag', 'ifs_contract_tag_rel',
        'contract_id', 'tag_id', string='合同标签')

    @api.depends('validity_period')
    def _compute_validity_period(self):
        for template in self:
            sel = str(template.validity_period / 12)
            selection = list(filter(lambda x: x[0] == sel, VALIDITY_PERIOD))
            if len(selection) > 0:
                template.validity_period_sel = sel
                template.validity_period_view = selection[0][1]
            else:
                template.validity_period_sel = False
                template.validity_period_view = '%d个月' % template.validity_period

    # Overrides of mail.render.mixin
    @api.depends('model')
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(
            default or {}, name=_("%s (copy)", self.name))
        return super(InclusiveFinancingContractTemplate, self).copy(default=default)

    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_window:
                template.ref_ir_act_window.unlink()
        return True

    def create_action(self):
        ActWindow = self.env['ir.actions.act_window']
        view = self.env.ref('mail.email_compose_message_wizard_form')

        # for template in self:
        #     button_name = _('Send Mail (%s)', template.name)
        #     action = ActWindow.create({
        #         'name': button_name,
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'mail.compose.message',
        #         'context': "{'default_composition_mode': 'mass_mail', 'default_template_id' : %d, 'default_use_template': True}" % (template.id),
        #         'view_mode': 'form,tree',
        #         'view_id': view.id,
        #         'target': 'new',
        #         'binding_model_id': template.model_id.id,
        #     })
        #     template.write({'ref_ir_act_window': action.id})

        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'validity_period_sel' in vals and vals.get('validity_period_sel', False):
                vals['validity_period'] = float(
                    vals.get('validity_period_sel', '2')) * 12

        return super().create(vals_list)

    def write(self, vals):
        if 'validity_period_sel' in vals and vals.get('validity_period_sel', False):
            vals['validity_period'] = float(
                vals.get('validity_period_sel', '2')) * 12

        return super().write(vals)

    def generate_contract(self, res_ids, fields):
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
                    options={
                        # 'render_safe': field == 'subject' 该属性不存在了,
                        'post_process': (field == 'body_html')  
                    },
                )
                for res_id, field_value in generated_field_values.items():
                    results.setdefault(res_id, dict())[field] = field_value
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # technical settings
                values.update(
                    # mail_server_id=template.mail_server_id.id or False,
                    # auto_delete=template.auto_delete,
                    model=template.model,
                    res_id=res_id or False,
                    # attachment_ids=[attach.id for attach in template.attachment_ids],
                )

            # Add report in attachments: generate once for all template_res_ids
            if template.report_template:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = template._render_field(
                        'report_name', [res_id])[res_id]
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = report._render_qweb_pdf([res_id])
                    else:
                        res = report._render([res_id])
                        if not res:
                            raise UserError(
                                _('Unsupported report type %s found.', report.report_type))
                        result, format = res

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return multi_mode and results or results[res_ids[0]]
