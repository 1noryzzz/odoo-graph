# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, UserError


class InclusiveFinancingInterestSolution(models.Model):
    _name = 'ifs.gar.partner.interest.solution'
    _description = '计息方案'
    _inherit = ['ifs.ir.sequence.mixin']

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'factor_id' in fields_list and not res.get('factor_id'):
            if 'factor' in (self.env.company.ifs_partners or []):
                factor = self.env['ifs.partner.factor'].search([
                    ('ifs_company_id.company_id.id', '=', self.env.company.id)
                ], limit=1)
                if factor.exists():
                    res.setdefault('factor_id', factor.id)
                else:
                    raise UserError(_('数据异常，当前公司未配置保理方！'))
            else:
                raise AccessDenied(_('仅保理方可设置计息方案！'))
        return res

    name = fields.Char('计息方案名称', required=True)
    factor_id = fields.Many2one('ifs.partner.factor', string='保理方', required=True)
    factor_supplier_ids = fields.One2many(
        'ifs.gar.partner.factor.supplier',
        'interest_solution_id',
        string='适用供应方',
        help='选定的供应方，其下子账户将使用本计息方案',
    )

    damages_rate = fields.Percent(
        '违约金率',
        default=0.025,
        help='违约金=总账单金额×此比例',
    )
    penalty_daily_rate = fields.Percent(
        '滞纳金日息',
        default=0.0007,
        help='滞纳金按日计息',
    )
    is_compound_interest = fields.Boolean(
        '是否复利',
        default=False,
        help='是否复利计息',
    )
