# -*- coding: utf-8 -*-

import base64
import json
import oss2

from aliyunsdkcore import client
from aliyunsdksts.request.v20150401 import AssumeRoleRequest
from odoo import api, models, fields


class OssClientMixin(models.AbstractModel):
    _name = 'oss.client.mixin'
    _description = "Aliyun OSS Mixin"

    def _retrieve_oss_sts_params(self):
        Config = self.env['ir.config_parameter'].sudo()
        max_per_batch = Config.get_param(
                'galaxy.aliyun.oss.max.perbatch', '100')
        if max_per_batch.isnumeric():
            max_per_batch = int(max_per_batch)
        else:
            max_per_batch = 100
        return dict(
            access_key_id=Config.get_param(
                'galaxy.aliyun.access.key.id'),
            access_secret=Config.get_param(
                'galaxy.aliyun.access.key.secret'),
            region_id=Config.get_param(
                'galaxy.aliyun.oss.region.id'),
            bucket_name=Config.get_param(
                'galaxy.aliyun.oss.bucket', 'galaxy'),
            endpoint=Config.get_param(
                'galaxy.aliyun.oss.endpoint', 'oss-cn-shenzhen.aliyuncs.com'),
            role_arn=Config.get_param(
                'galaxy.aliyun.oss.role.arn'),
            max_per_batch=max_per_batch
        )

    def get_oss_sts(self):
        sts_params = self._retrieve_oss_sts_params()

        clt = client.AcsClient(
            sts_params.get('access_key_id'),
            sts_params.get('access_secret'),
            sts_params.get('region_id'))
        req = AssumeRoleRequest.AssumeRoleRequest()
        req.set_accept_format('json')
        req.set_RoleArn(sts_params.get('role_arn'))
        req.set_RoleSessionName('session-js-put')
        req.set_Policy(json.dumps({
            'Version': '1',
            'Statement': [{
                'Action': ['oss:GetObject', 'oss:PutObject'],
                'Effect': 'Allow',
                'Resource': ['acs:oss:*:*:%s/*' % sts_params.get('bucket_name')]
            }]
        }))
        body = clt.do_action_with_exception(req)
        credits = json.loads(oss2.to_unicode(body)).get('Credentials')
        credits.update({
            'Endpoint': sts_params.get('endpoint'),
            'Bucket': sts_params.get('bucket_name'),
            'Region': 'oss-%s' % sts_params.get('region_id'),
            'MaxPerBatch': sts_params.get('max_per_batch'),
        })
        return credits

    @api.model
    def create_with_oss(self, oss_objects):
        oss_params = self._retrieve_oss_sts_params()
        bucket = oss2.Bucket(
            oss2.Auth(
                oss_params.get('access_key_id'),
                oss_params.get('access_secret')),
            oss_params.get('endpoint'),
            oss_params.get('bucket_name'))

        oss_datas = []
        for oss_object in oss_objects:
            oss_datas.append(base64.b64encode(
                bucket.get_object(oss_object.get('oss_key')).read() or b'').decode('utf8'))
            bucket.delete_object(oss_object.get('oss_key'))

        return oss_datas
    
    @api.model
    def betch_update_finish(self, res_ids):
        return {
            'result': len(res_ids)
        }
