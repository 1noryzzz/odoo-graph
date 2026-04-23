# -*- coding: utf-8 -*-
import json
import logging

from odoo import SUPERUSER_ID, api, fields, models

_logger = logging.getLogger(__name__)


class OACallbackLog(models.Model):
    _description = '回调日志'
    _name = 'oa.callback.log'
    _rec_name = 'create_date'

    company_id = fields.Many2one(
        'res.company', string='公司', required=True,
        ondelete="cascade", default=lambda self: self.env.company.id)
    event_type = fields.Char(string="消息类型", required=True)
    body = fields.Text(string="消息内容")
    source = fields.Char("消息来源")
    target = fields.Char("消息目标")
    callback_action_id = fields.Many2one(
        'oa.callback.action', string='回调处理动作', ondelete="cascade", required=True)
    result = fields.Char("处理返回结果")

    def _get_msg_body(self, message):
        if isinstance(message, str):
            return message
        elif isinstance(message, dict):
            return json.dumps(message)

        return ''
    
    @api.autovacuum
    def _gc_old_log(self):
        _logger.warning("++++++++++++++callback log gc not implement++++++++++")

    def info(self, company_id, event_type, callback_action, message, source=None, target=None):
        """
        记录下来自第三方平台的消息回调
        :return:
        """
        return self.env['oa.callback.log'].create({
            'company_id': company_id,
            'event_type': event_type,
            'callback_action_id': callback_action.id,
            'body': self._get_msg_body(message),
            'source': source or callback_action.value_from,
            'target': target,
        })
