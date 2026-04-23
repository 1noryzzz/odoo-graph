# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields


class InclusiveFinancingStepsWizard(models.AbstractModel):
    _name = 'ifs.steps.wizard'
    _description = '弹窗向导界面'
    _step_models = []

    current_step = fields.Integer(
        compute='_compute_current_step', string='当前步骤')
    is_in_step = fields.Boolean(
        compute='_compute_current_step', string='是否在向导步骤中')
    has_prev_step = fields.Boolean(
        compute='_compute_current_step', string='是否有上一步')
    has_next_step = fields.Boolean(
        compute='_compute_current_step', string='是否有下一步')

    def _next_model(self, current_model):
        if not current_model:
            return False

        (c_index, hit) = reduce(lambda x, y: (x[0], True) if x[1] or y == current_model else (
            x[0] + 1, False), self._step_models, (0, False))
        return self._step_models[c_index + 1] if hit and len(self._step_models) > (c_index + 1) else False

    def _current_step(self, current_model):
        if not current_model:
            return False

        (c_index, hit) = reduce(lambda x, y: (x[0], True) if x[1] or y == current_model else (
            x[0] + 1, False), self._step_models, (0, False))
        return c_index + 1 if hit else False

    def _compute_current_step(self):
        for record in self:
            record.update({
                'current_step': 1,
                'is_in_step': (
                    self._context.get('prev_model', False) or self._context.get(
                        'next_model', False)
                ) and True,
                'has_prev_step': self._context.get('prev_model', False) and True,
                'has_next_step': self._context.get('next_model', False) and True,
            })
