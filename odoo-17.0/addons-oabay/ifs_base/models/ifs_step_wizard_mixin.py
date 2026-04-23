# -*- coding: utf-8 -*-

from odoo import _, models


class InclusiveFinancingStepWizardMixin(models.AbstractModel):
    _name = 'ifs.step.wizard.mixin'
    _description = '流程步骤主模型'
    _ref_id_field = ''
    _ref_model = ''

    # ref_model_id = fields.Many2one('ifs.step.by.step.mixin')
    # current_step = fields.Integer(
    #     related='ref_model_id.current_step', string='当前步骤')
    # has_prev_step = fields.Boolean(
    #     related='ref_model_id.has_prev_step', string='是否有上一步')
    # has_next_step = fields.Boolean(
    #     related='ref_model_id.has_next_step', string='是否有下一步')
    # prev_model = fields.Char(
    #     related='ref_model_id.prev_model', string='上一步对应的模型')
    # next_model = fields.Char(
    #     related='ref_model_id.next_model', string='下一步对应的模型')

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, record._description))
        return res

    def step_info(self, ref_id):
        step = self.search([(self._ref_id_field, '=', ref_id)], limit=1)
        return (step.id, self._name)

    def nosave_prev(self):
        if self[self._ref_id_field]:
            return self[self._ref_id_field].nosave_prev()
        else:
            return self.env[self._ref_model].browse(self._context.get(f'default_{self._ref_id_field}')).nosave_prev()

    def nosave_refresh(self):
        if self[self._ref_id_field]:
            return self[self._ref_id_field].nosave_refresh()
        else:
            return self.env[self._ref_model].browse(self._context.get(f'default_{self._ref_id_field}')).nosave_refresh()

    def action_next(self):
        return self[self._ref_id_field].action_next()
