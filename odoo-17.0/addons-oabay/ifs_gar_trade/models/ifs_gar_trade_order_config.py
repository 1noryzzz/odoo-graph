# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError


class GuaranteeAccountsRecTradeDefinition(models.Model):
    _name = 'ifs.gar.trade.definition'
    _description = '交易订单流程参数设置'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', '参数表名称已存在！')
    ]

    name = fields.Char('参数表名称', required=True, index=True)
    params_definition = fields.PropertiesDefinition('参数配置')


class GuaranteeAccountsRecTradeOrderConfig(models.Model):
    _name = 'ifs.gar.trade.order.config'
    _description = '交易订单块配置'
    _order = 'factor_id, supplier_id'

    _sql_constraints = [
        ('factor_id_supplier_id_uniq', 'unique (factor_id, supplier_id)', '已存在生效的配置')
    ]

    def name_get(self):
        res = []
        for record in self:
            name = record.factor_id.name
            if record.supplier_id:
                name += ' - ' + record.supplier_id.name
            else:
                name += ' - 全局'
            res.append((record.id, name))
        return res

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'factor_id' in fields and not res.get('factor_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                factor = self.env['ifs.partner.factor'].search([
                    ('ifs_company_id.company_id.id', '=', self.env.company.id)
                ], limit=1)
                if factor.exists():
                    res.setdefault('factor_id', factor.id)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可设置采购方进件流程参数！'))
        return res

    factor_id = fields.Many2one(
        'ifs.partner.factor', string='保理方', required=True, index=True, ondelete='cascade')
    # 此设置参数生效的保理方，为空则为全局设置
    supplier_id = fields.Many2one(
        'ifs.partner.supplier', string='供应方', ondelete='cascade')
    detail_ids = fields.One2many(
        'ifs.gar.trade.order.config.detail', 'config_id', string='交易订单参数设置明细')
    is_global = fields.Boolean('是否全局设置', compute='_compute_is_global')

    @api.depends('supplier_id')
    def _compute_is_global(self):
        for record in self:
            record.is_global = not record.supplier_id

    def retrieve_config(self, factor_id, supplier_id, detail_codes):
        configs = self.search([
            ('factor_id', '=', factor_id),
            '|',
            ('supplier_id', '=', supplier_id),
            ('supplier_id', '=', False)
        ])

        supplier_config = configs.filtered(
            lambda r: r.supplier_id.id == supplier_id)
        if not supplier_config.id and len(configs.ids) > 0:
            # 如果不存在针对当前供应方的配置，则取全局配置
            supplier_config = configs[0]

        return supplier_config.detail_ids.filtered(lambda r: r.code in detail_codes)


class GuaranteeAccountsRecTradeOrderConfigDetail(models.Model):
    _name = 'ifs.gar.trade.order.config.detail'
    _description = '交易订单参数设置明细'
    _order = 'sequence'

    sequence = fields.Integer('序号', default=10)
    config_id = fields.Many2one(
        'ifs.gar.trade.order.config', string='进件流程参数设置', required=True, index=True, ondelete='cascade')
    code = fields.Char('参数编码', required=True, index=True)
    name = fields.Char('参数名称', required=True)
    type = fields.Selection([
        ('block', '静态区块'),
        ('jsonb', '属性配置块')
    ], string='参数类型', required=True)
    is_visible = fields.Boolean('是否显示', default=True)
    is_required = fields.Boolean('是否必填', default=True)

    has_definition = fields.Boolean(
        '是否有属性配置', compute='_compute_has_definition')
    definition_id = fields.Many2one(
        'ifs.gar.trade.definition', string='属性配置', ondelete='restrict')
    sample = fields.Properties(
        '属性内容示例', definition='definition_id.params_definition')
    remark = fields.Text('备注')

    @api.depends('type')
    def _compute_has_definition(self):
        for record in self:
            record.has_definition = record.type == 'jsonb'

    def validate_required(self, vals):
        err_msgs = []
        if self.definition_id.id and self.is_visible and self.is_required:
            for definition in self.definition_id.params_definition:
                name = definition.get('name')
                type = definition.get('type')
                string = definition.get('string')
                if type == 'char' and len((vals.get(name, '') or '').strip()) == 0:
                    err_msgs.append(string)
                elif type == 'float' and vals.get(name, 0) <= 0:
                    err_msgs.append(string)
                elif type == 'integer' and vals.get(name, 0) <= 0:
                    err_msgs.append(string)
                elif type == 'date' and len((vals.get(name, '') or '').strip()) == 0:
                    err_msgs.append(string)
                elif type == 'datetime' and len((vals.get(name, '') or '').strip()) == 0:
                    err_msgs.append(string)
                elif type == 'selection' and len((vals.get(name, '') or '').strip()) == 0:
                    err_msgs.append(string)

        return err_msgs
