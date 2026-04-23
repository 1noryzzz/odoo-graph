# -*- coding: utf-8 -*-

import json

from odoo import _, api, models, fields
import requests,json,time,hashlib
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta


class InclusiveFinancingMessage(models.Model):
    _name = 'ifs.message'
    _description = '消息推送'
    
    open_app_id = fields.Many2one('galaxy.open.api.app',string="开放平台第三方应用")
    message_type = fields.Selection([('approval','approval'),('pay','pay'),('bill','bill')],string="消息类型")
    message_body = fields.Json("消息内容")
    success = fields.Boolean("是否推送成功",default=False)
    push_count = fields.Integer("推送次数",default=0)
    push_record_ids = fields.One2many('ifs.message.push.record','message_id',string="推送记录")
    response_data = fields.Json("响应结果",compute="_compute_response")
    
    def _compute_response(self):
        for record in self:
            record.response_data = False
            if record.push_record_ids:
                push_record_ids = sorted(record.push_record_ids, key=lambda record: record.create_date,reverse=True)
                try:
                    record.response_data = json.loads(push_record_ids[0].response_text)
                except Exception:
                    pass

    def push(self):
        cfg = self.env['ir.config_parameter'].sudo()
        secretKey = cfg.get_param('ifs.gar.entry.hezongyy.secret.key', '')
        systemtimestamp = int(time.time())
        systemsign = hashlib.sha1(
            f'{systemtimestamp}{secretKey}'.encode('utf-8')).hexdigest()
        headers = {
            'systemtimestamp': str(systemtimestamp),
            'systemsign': systemsign.upper()
        }
        try:
            response = requests.request(url=self.open_app_id.message_handler_url, method=self.open_app_id.request_method.lower(), headers=headers, json={
                'id': self.id,
                'message_type': self.message_type,
                'message_body': self.message_body})
            self.push_count = self.push_count + 1
            if response.status_code == 200:
                self.success = True
            self.env['ifs.message.push.record'].sudo().create({
                'message_id': self.id,
                'response_status_code': response.status_code,
                'response_text': response.text
            })
        except Exception as e:
            self.push_count = self.push_count + 1
            self.env['ifs.message.push.record'].create({
                'message_id':self.id,
                'error_msg':str(e)
            })
            
                
    def _push(self):
        cfg = self.env['ir.config_parameter'].sudo()
        secretKey = cfg.get_param('ifs.gar.entry.hezongyy.secret.key', '')
        systemtimestamp  = int(time.time()) 
        systemsign = hashlib.sha1(f'{systemtimestamp}{secretKey}'.encode('utf-8')).hexdigest()
        headers = {
            'systemtimestamp':str(systemtimestamp),
            'systemsign':systemsign.upper()
        }
        fail_number = 0
        for record in self:
            try:
                response = requests.request(url=record.open_app_id.message_handler_url, method=record.open_app_id.request_method.lower(),headers=headers, json={
                    'id':record.id,
                    'message_type': record.message_type,
                    'message_body': record.message_body})
                record.push_count = record.push_count + 1
                if response.status_code == 200:
                    record.success = True
                else:
                    fail_number += 1
                self.env['ifs.message.push.record'].sudo().create({
                    'message_id':record.id,
                    'response_status_code':response.status_code,
                    'response_text':response.text
                })
            except Exception as e:
                fail_number += 1
                record.push_count = record.push_count + 1
                self.env['ifs.message.push.record'].create({
                    'message_id':record.id,
                    'error_msg':str(e)
                })
        return fail_number
    
    def push_all(self,re_push=0):
        records = self.sudo().search([('success','=',False)])
        fail_number = records._push()
        if fail_number > 0 and re_push == 0:
            cron = self.env['ir.cron'].sudo().env.ref(
            'ifs_gar_entry.push_all')
            self.env['ir.cron.trigger'].sudo().create({'cron_id': cron.id,
                                                          'call_at': datetime.now() + relativedelta(seconds=60)
                                                          })
            
    
    def trigger_push(self,open_app_id,message_type,message_body):
        self.sudo().create({
            'open_app_id': open_app_id.id,
            'message_type': message_type,
            'message_body': message_body
        })
        cron = self.env['ir.cron'].sudo().env.ref(
            'ifs_gar_entry.push_all')
        self.env['ir.cron.trigger'].sudo().create(
            {'cron_id': cron.id, 'call_at': datetime.now() +
             relativedelta(seconds=2)}
        )

class InclusiveFinancingMessagePushRecord(models.Model):
    _name = 'ifs.message.push.record'
    _description = '消息推送记录'
    
    message_id = fields.Many2one('ifs.message',string="消息id")
    response_status_code = fields.Integer("响应状态码")
    response_text = fields.Text("响应信息")
    error_msg = fields.Text("错误信息")
    