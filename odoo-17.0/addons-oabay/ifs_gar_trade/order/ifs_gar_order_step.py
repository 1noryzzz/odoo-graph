# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecOrderStep(models.AbstractModel):
    _name = 'ifs.gar.order.step'
    _inherit = ['ifs.step.wizard.mixin']
    _ref_id_field = 'trade_order_id'
    _ref_model = 'ifs.gar.trade.order'
    _description = '订单创建流程步骤'

    trade_order_id = fields.Many2one('ifs.gar.trade.order')
    current_step = fields.Integer(
        related='trade_order_id.current_step', string='当前步骤')
    has_prev_step = fields.Boolean(
        related='trade_order_id.has_prev_step', string='是否有上一步')
    has_next_step = fields.Boolean(
        related='trade_order_id.has_next_step', string='是否有下一步')
    prev_model = fields.Char(
        related='trade_order_id.prev_model', string='上一步对应的模型')
    next_model = fields.Char(
        related='trade_order_id.next_model', string='下一步对应的模型')
