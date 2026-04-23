# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecEntryStep(models.AbstractModel):
    _name = 'ifs.gar.entry.step'
    _inherit = ['ifs.step.wizard.mixin']
    _ref_id_field = 'entry_id'
    _description = '进件流程步骤模型'

    entry_id = fields.Many2one('ifs.gar.entry.mixin')
    ifs_company_id = fields.Many2one(
        'ifs.base.company', related='entry_id.ifs_company_id')
    current_step = fields.Integer(
        related='entry_id.current_step', string='当前步骤')
    has_prev_step = fields.Boolean(
        related='entry_id.has_prev_step', string='是否有上一步')
    has_next_step = fields.Boolean(
        related='entry_id.has_next_step', string='是否有下一步')
    prev_model = fields.Char(
        related='entry_id.prev_model', string='上一步对应的模型')
    next_model = fields.Char(
        related='entry_id.next_model', string='下一步对应的模型')

    # def name_get(self):
    #     res = []
    #     for record in self:
    #         res.append((record.id, record._description))
    #     return res

    # def step_info(self, entry_id):
    #     step = self.search([('entry_id', '=', entry_id)], limit=1)
    #     return (step.id, self._name)

    # def nosave_prev(self):
    #     if self.entry_id:
    #         return self.entry_id.nosave_prev()
    #     else:
    #         return self.env[self._entry_model].browse(self._context.get('default_entry_id')).nosave_prev()

    # def nosave_refresh(self):
    #     if self.entry_id:
    #         return self.entry_id.nosave_refresh()
    #     else:
    #         return self.env[self._entry_model].browse(self._context.get('default_entry_id')).nosave_refresh()

    # def action_next(self):
    #     return self.entry_id.action_next()
