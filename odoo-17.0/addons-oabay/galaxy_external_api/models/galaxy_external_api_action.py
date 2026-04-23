# -*- coding: utf-8 -*-

import logging
import xmltodict
import time
import random
import hashlib
import odoo
import werkzeug
from datetime import timedelta,datetime
from werkzeug.exceptions import BadRequest

from odoo import _, api, models, tools, fields
from odoo.exceptions import UserError
from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)


class GalaxyExternalApiPublic(models.AbstractModel):
    _name = 'galaxy.external.api.public'
    _description = 'API动作处理用的公共模型'
    
    @api.model
    def generate_serial_number(self,prefix="",suffix="",format=False):
        if format:
            timestamp = (datetime.utcnow()+timedelta(hours=8)).strftime(format)
        else:
            timestamp = int(time.time() * 1000) 
        rand_num = str(random.randint(100, 999))
        return f'{prefix}{timestamp}{rand_num}{suffix}'
    
    @api.model
    def md5hlhex(self,data):
        md5hl = hashlib.md5()
        md5hl.update(data.encode('utf8'))
        return md5hl.hexdigest()
    
    def now_datetime(self,format=False,utc=False):
        now  = datetime.now()
        if isinstance(utc,int):
            now = datetime.utcnow() + timedelta(hours=utc)
        if format:
            return now.strftime(format)
        return now

class GalaxyExternalApiDummy(models.AbstractModel):
    _name = 'galaxy.external.api.dummy'
    _inherit = 'galaxy.external.api.public'
    _description = 'API动作处理用的空模型'

class GalaxyExternalApiXml(models.AbstractModel):
    _name = 'galaxy.external.api.xml'
    _inherit = 'galaxy.external.api.public'
    _description = 'API动作处理用的xml帮助类'

    @api.model
    def to_xml_string(self, dict_data, root_tag='xml'):
        elem = ET.Element(root_tag)
        for key, val in dict_data.items():
            child = ET.Element(key)
            child.text = str(val)
            elem.append(child)
        return ET.tostring(elem)

    @api.model
    def parse_xml_dict(self, xml_string, root_tag='xml'):
        return xmltodict.parse(xml_string)[root_tag]


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    usage = fields.Selection(selection_add=[
        ('api_pre_action', u'API预执行动作'),
        ('api_post_action', u'API后执行动作')
    ], ondelete={'api_pre_action': 'cascade', 'api_post_action': 'cascade'})

    @api.model
    def _get_eval_context(self, action=None):
        eval_context = super(
            IrActionsServer, self)._get_eval_context(action=action)
        eval_context.update({
            'json': tools.safe_eval.json,
            'BadRequest': werkzeug.exceptions.BadRequest,
            'AccessDenied': odoo.exceptions.AccessDenied,
            'ValidationError': odoo.exceptions.ValidationError
        })
        return eval_context


class GalaxyExternalApiAction(models.Model):
    _name = 'galaxy.external.api.action'
    _description = "外部接口动作"
    _order = 'sequence, write_date desc'

    _sql_constraints = [
        ('action_name_uniq', 'unique(action_name)', u'动作名称重复!'),
    ]

    api_id = fields.Many2one(
        'galaxy.external.api', string='接口', required=True, index=True, ondelete='cascade')
    ir_actions_server_id = fields.Many2one(
        'ir.actions.server', 'Server action',
        delegate=True, ondelete='restrict', required=True)
    action_name = fields.Char(
        string='动作名称', related='ir_actions_server_id.name', store=True, readonly=False)
    rollback = fields.Boolean(u'是否回滚', default=True)
    active = fields.Boolean('可用', default=True)
    sequence = fields.Integer('Sequence', default=10)

    lastcall = fields.Datetime(string='最后调用时间')

    @api.model
    def default_get(self, fields_list):
        if not self._context.get('default_state'):
            self = self.with_context(default_state='code')
        return super(GalaxyExternalApiAction, self).default_get(fields_list)

    def _result_update(self, action, **args):
        if type(action) is dict:
            for key, value in action.items():
                if key != 'response' and key in args:
                    args.get(key, {}).update({
                        **value
                    })

    def process(self, **args):
        """
        args里包含的参数有：
            headers
            query
            body
            response 返回的response 对象
            last_result 上一次处理的结果
            api_request 此次请求的记录
        """
        action = {}
        self.ensure_one()
        if self.active:
            self.check_access_rights('write')
            try:
                action = self.with_context(
                    **args,
                    lastcall=self.lastcall,
                    api_action=self).ir_actions_server_id.run()
                self.lastcall = fields.Datetime.now()
                self._result_update(action, **args)
            except Exception as e:
                _logger.exception(
                    "Call action %s for server action #%s failed", self.action_name, self.ir_actions_server_id)
                self._handle_callback_exception(
                    self.action_name, self.ir_actions_server_id, e)
        return action

    @api.model
    def _handle_callback_exception(self, action_name, server_action_id, job_exception):
        """ Method called when an exception is raised by a job.

        Simply logs the exception and rollback the transaction. """
        if type(job_exception) is UserError:
            if self.usage == 'api_pre_action' or self.rollback:
                self._cr.rollback()
            raise job_exception
        elif type(job_exception) is BadRequest:
            if self.usage == 'api_pre_action' or self.rollback:
                self._cr.rollback()
            raise job_exception
        else:
            self._cr.rollback()
            
    def unlink(self):
        server_actions = self.with_context(force_delete=True).mapped('ir_actions_server_id')
        res = super().unlink()
        server_actions.unlink()
        return res
