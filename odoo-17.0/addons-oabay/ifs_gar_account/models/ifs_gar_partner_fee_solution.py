# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError
from random import randint


class InclusiveFinancingFeeSolution(models.Model):
    _name = 'ifs.gar.partner.fee.solution'
    _description = '收费方案'
    _inherit = ['ifs.ir.sequence.mixin']

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
                raise AccessDenied(_('仅保理方可设置收费方案！'))
        return res

    name = fields.Char('收费方案名称', required=True)
    factor_id = fields.Many2one('ifs.partner.factor', string='保理方')
    company_id = fields.Many2one(
        'res.company', string='公司', related='factor_id.company_id')
    # factor_supplier_ids = fields.One2many(
    #     'ifs.gar.partner.factor.supplier', 'fee_solution_id', string='保理方与供应方关联关系')
    ver_solution_ids = fields.One2many(
        'ifs.gar.partner.fee.solution.ver', compute='_compute_ver_solution_ids', string='收费方案')
    last_ver_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution.ver', compute='_compute_last_ver_solution', string='最后一个版本的收费方案', store=True)
    supplier_ids = fields.One2many(
        related='last_ver_solution_id.supplier_ids', string='选择该收费方案的供应方')
    description = fields.Text(
        related='last_ver_solution_id.description', string='收费方案描述', readonly=False)
    contract_content = fields.Html(
        related='last_ver_solution_id.contract_content', string='收费方案合同内容', readonly=False)
    rule_ids = fields.One2many(
        related='last_ver_solution_id.rule_ids', string='计费规则', readonly=False)

    # @api.depends('ver_solution_ids')
    # def _compute_last_ver_solution(self):
    #     for record in self:
    #         if record.ver_solution_ids:
    #             record.last_ver_solution_id = record.ver_solution_ids[0]
    #         else:
    #             record.last_ver_solution_id = False

    @api.depends('name')
    def _compute_ver_solution_ids(self):
        for record in self:
            ver_solution_ids = self.env['ifs.gar.partner.fee.solution.ver'].search(
                [('fee_solution_id', '=', record.id)], order='version DESC')
            record.ver_solution_ids = ver_solution_ids if ver_solution_ids else []
                
    @api.depends('ver_solution_ids')
    def _compute_last_ver_solution(self):
        for record in self:
            if record.ver_solution_ids:
                record.last_ver_solution_id = record.ver_solution_ids[0]
            else:
                record.last_ver_solution_id = False

    def create_solution_ver(self):
        return {
            'name': _('收费方案'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.gar.partner.fee.solution.ver',
            'target': 'new',
        }

    def view_solution_ver(self):
        if self.last_ver_solution_id:
            return {
                'name': _('收费方案'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.partner.fee.solution.ver',
                'res_id': self.last_ver_solution_id.id,
                'target': 'new',
            }


class InclusiveFinancingFeeSolutionVersion(models.Model):
    _name = 'ifs.gar.partner.fee.solution.ver'
    _description = '收费方案'
    _inherits = {'ifs.gar.partner.fee.solution': 'fee_solution_id'}
    _order = 'version desc'
    _rec_name = 'name'

    @api.depends('name', 'version')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.version:
                name = record.name + ' , 版本: ' + str(record.version)
            res.append((record.id, name))
        return res

    fee_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution', string='收费方案', required=True, ondelete='cascade')
    version = fields.Integer('版本', default=1, required=True, readonly=True)
    description = fields.Text('收费方案描述')
    contract_content = fields.Html('收费方案合同内容')
    rule_ids = fields.One2many(
        'ifs.gar.partner.fee.rule', 'ver_solution_id', string='计费规则')
    factor_supplier_ids = fields.One2many(
        'ifs.gar.partner.factor.supplier', 'fee_solution_id', string='使用此方案的供应方')
    supplier_ids = fields.One2many(
        'ifs.partner.supplier', compute='_compute_supplier_ids', string='选择该收费方案的供应方')

    @api.depends('factor_supplier_ids')
    def _compute_supplier_ids(self):
        for record in self:
            if record.factor_supplier_ids:
                record.supplier_ids = [fields.Command.set(
                    record.factor_supplier_ids.supplier_id.ids)]
            else:
                record.supplier_ids = False

    def calc_amount_fee(self, factor_supplier_id, amount):
        fee_amount = 0.0
        for rule in self.rule_ids:
            fee = rule.fee_mode.calc_fee(factor_supplier_id, amount, fee_amount)
            fee_amount += fee
        return fee_amount

    def view_version_solution(self):
        if self.ver_solution_ids:
            return {
                'name': _('收费方案'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.partner.fee.solution.ver',
                'res_id': False,
                'target': 'current',
                'domain': [('id', 'in', self.ver_solution_ids.ids)],
            }

    def view_solution_ver(self):
        return {
            'name': _('收费方案'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.gar.partner.fee.solution.ver',
            'res_id': self.id,
            'target': 'new',
        }

    def write(self, vals):
        if 'rule_ids' in vals or 'contract_content' in vals:
            for rule in vals.get('rule_ids', []):
                if rule[0] == 4:
                    fee_rule = self.env['ifs.gar.partner.fee.rule'].browse(
                        rule[1])
                    rule[0] = 0
                    rule[1] = 0
                    rule[2] = {
                        'ver_solution_id': fee_rule.ver_solution_id.id,
                        'fee_mode': fee_rule.fee_mode._name + ',' + str(fee_rule.fee_mode.id),
                        'fee_type': fee_rule.fee_type.id,
                    }
                elif rule[0] == 1:
                    fee_rule = self.env['ifs.gar.partner.fee.rule'].browse(
                        rule[1])
                    rule[0] = 0
                    rule[1] = 0
                    if 'ver_solution_id' not in rule[2]:
                        rule[2].update(
                            {'ver_solution_id': fee_rule.ver_solution_id.id})
                    if 'fee_mode' not in rule[2]:
                        rule[2].update(
                            {'fee_mode': fee_rule.fee_mode._name + ',' + str(fee_rule.fee_mode.id)})
                    if 'fee_type' not in rule[2]:
                        rule[2].update({'fee_type': fee_rule.fee_type.id})
                elif rule[0] == 2:
                    vals.get('rule_ids').remove(rule)
            vals = {
                'fee_solution_id': self.fee_solution_id.id,
                'description': vals.get('description') if 'description' in vals else self.description,
                'contract_content': vals.get('contract_content') if 'contract_content' in vals else self.contract_content,
                'rule_ids': vals.get('rule_ids') if 'rule_ids' in vals else [fields.Command.set(self.rule_ids.ids)],
                'version': self.last_ver_solution_id.version + 1,
            }
            return self.create(vals)
        else:
            return super().write(vals)


class InclusiveFinancingFeeRule(models.Model):
    _name = 'ifs.gar.partner.fee.rule'
    _description = '计费规则'

    ver_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution.ver', string='收费方案')
    fee_type = fields.Many2one(
        'ifs.gar.partner.fee.type', string='收费项', required=True)
    fee_mode = fields.Reference(selection=[], string='计费方式')
    formula = fields.Char('计费公式', compute='_compute_formula')

    @api.depends('fee_mode')
    def _compute_formula(self):
        for record in self:
            record.formula = record.fee_mode.formula if record.fee_mode else False


class InclusiveFinancingFeeType(models.Model):
    _name = 'ifs.gar.partner.fee.type'
    _description = '计费项目'

    def _get_default_color(self):
        return randint(1, 11)

    # 年费、保理服务费、系统使用费、保证金、违约金、其他
    name = fields.Char('计费项目名称', required=True)
    code = fields.Char('计费项目编码', required=True)
    color = fields.Integer(string='标签颜色', default=_get_default_color)
    remark = fields.Text('备注')
