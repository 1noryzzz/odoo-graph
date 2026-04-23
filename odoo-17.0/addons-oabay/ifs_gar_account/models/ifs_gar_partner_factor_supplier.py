# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InclusiveFinancingGarPartnerFactorSupplier(models.Model):
    _inherit = 'ifs.gar.partner.factor.supplier'

    @api.depends('supplier_id', 'supplier_id.name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.supplier_id.name if record.supplier_id else f'ID:{record.id}'

    currency_id = fields.Many2one(
        'res.currency', string='币种', related='supplier_id.currency_id')
    cut_off_time = fields.Float('日切时间', default=4.5)
    cut_off_cron_id = fields.Many2one(
        'ir.cron', string='日切定时任务', ondelete='set null')
    fee_solution_id = fields.Many2one(
        'ifs.gar.partner.fee.solution.ver', string='收费方案')
    interest_solution_id = fields.Many2one(
        'ifs.gar.partner.interest.solution', string='计息方案')

    total_quota = fields.Monetary('最高合作额度', default=100000000.0)
