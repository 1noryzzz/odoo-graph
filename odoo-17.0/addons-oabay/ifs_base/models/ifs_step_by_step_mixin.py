# -*- coding: utf-8 -*-

from functools import reduce
from odoo import _, api, models, fields


class InclusiveFinancingStepByStepMixin(models.AbstractModel):
    _name = 'ifs.step.by.step.mixin'
    _description = '分步骤录入信息的主模型'
    _ref_id_field = ''

    def _step_models(self):
        return []

    current_model = fields.Char(
        '当前进件步骤对应的模型', required=True, default=lambda self: self._step_models()[0], copy=False)
    current_step = fields.Integer(
        compute='_compute_step', string='当前步骤')
    has_prev_step = fields.Boolean(
        compute='_compute_step', string='是否有上一步')
    has_next_step = fields.Boolean(
        compute='_compute_step', string='是否有下一步')
    prev_model = fields.Char(
        compute='_compute_step', string='上一步对应的模型')
    next_model = fields.Char(
        compute='_compute_step', string='下一步对应的模型')

    @api.depends('current_model')
    def _compute_step(self):
        step_models = self._step_models()
        for record in self:
            (c_index, hit) = reduce(lambda x, y: (x[0], True) if x[1] or record.current_model.startswith(y) else (
                x[0] + 1, False), step_models, (0, False))

            current_step = (c_index + 1) if hit else 1
            record.update({
                'current_step': current_step,
                'has_prev_step': current_step > 1,
                'has_next_step': current_step < len(step_models),
                'prev_model': step_models[current_step - 2] if current_step > 1 else False,
                'next_model': step_models[current_step] if current_step < len(step_models) else False,
            })

    def _step_action(self, res_id, step_model, target='current'):
        return {
            'name': self.env[step_model]._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': step_model,
            'res_id': res_id,
            'target': target,
            'context': {
                f'default_{self._ref_id_field}': self.id,
                'no_breadcrumbs': True,
            }
        }

    def start_step(self, target='current'):
        first_model = self._step_models()[0]
        if self.current_model:
            first_model = self.current_model
        else:
            self.write({
                'current_model': first_model,
            })
        (res_id, step_model) = self.env[first_model].step_info(self.id)
        return self._step_action(res_id, step_model, target)

    def nosave_prev(self, target='current'):
        if self.has_prev_step:
            prev_model = self.prev_model
            self.write({
                'current_model': prev_model,
            })
            (res_id, step_model) = self.env[prev_model].step_info(self.id)
            return self._step_action(res_id, step_model, target)

    def nosave_refresh(self, target='current'):
        if self.current_model:
            current_model = self.current_model
            (res_id, step_model) = self.env[current_model].step_info(self.id)
            return self._step_action(res_id, step_model, target)

    def action_next(self, target='current'):
        if self.has_next_step:
            next_model = self.next_model
            self.write({
                'current_model': next_model,
            })
            (res_id, step_model) = self.env[next_model].step_info(self.id)
            return self._step_action(res_id, step_model, target)
