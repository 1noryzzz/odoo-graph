# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OACallbackActions(models.Model):
    _name = 'oa.callback.action'
    _description = "回调处理动作"
    _rec_name = 'callback_name'
    _order = 'sequence'

    ir_actions_server_id = fields.Many2one(
        'ir.actions.server', 'Server action',
        delegate=True, ondelete='restrict', required=True)
    #usage = fields.Selection(related='ir_actions_server_id.usage')
    callback_name = fields.Char(
        string='回调名称', related='ir_actions_server_id.name', store=True, readonly=False)
    user_id = fields.Many2one(
        'res.users', string='操作用户', default=lambda self: self.env.user, required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence', default=0)
    value_code_ids = fields.Many2many(
        'oa.callback.code', string=u'回调类型列表', copy=False, required=True)
    value_from = fields.Selection([('unknown', '未定义')], string=u'事件来源',
                                  store=True, compute='_compute_value_from')
    color = fields.Integer(string=u'color')
    lastcall = fields.Datetime(string='最后调用时间')

    _sql_constraints = [
        ('callback_name_uniq', 'unique(callback_name)', u'回调名称重复!'),
    ]

    @api.model
    def create(self, values):
        values['usage'] = 'oa_callback'
        return super(OACallbackActions, self).create(values)

    @api.model
    def default_get(self, fields_list):
        if not self._context.get('default_state'):
            self = self.with_context(default_state='code')
        return super(OACallbackActions, self).default_get(fields_list)

    @api.depends('value_code_ids')
    def _compute_value_from(self):
        for res in self:
            for co in res.value_code_ids:
                res.value_from = co.value_from
                break

    @api.constrains('value_code_ids', 'value_from')
    def _constrains_value_from(self):
        for res in self:
            if res.value_from:
                for co in res.value_code_ids:
                    if co.value_from != res.value_from:
                        raise ValidationError(u'回调类型列表中，只可选择相同来源的事件！')

    def process(self, entry, message, callback_log):
        self.ensure_one()
        self.check_access_rights('write')
        action = {}
        try:
            action = self.with_user(self.user_id).with_context(
                lastcall=self.lastcall,
                entry=entry,
                message=message,
                callback_action=self,
                callback_log=callback_log).ir_actions_server_id.run()
            self.lastcall = fields.Datetime.now()
        except Exception as e:
            _logger.exception("Call from callback action %s for server action #%s failed",
                              self.callback_name, self.ir_actions_server_id)
            self._handle_callback_exception(
                self.callback_name, self.ir_actions_server_id, e)
        return action

    @api.model
    def _handle_callback_exception(self, callback_name, server_action_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction. """
        self._cr.rollback()

    @api.model
    def toggle(self, model, domain):
        active = bool(self.env[model].search_count(domain))
        return self.write({'active': active})
