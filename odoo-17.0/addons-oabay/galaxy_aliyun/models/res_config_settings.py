# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    aliyun_access_key_id = fields.Char(
        string="AK_Id", config_parameter='galaxy.aliyun.access.key.id')
    aliyun_access_key_secret = fields.Char(
        string="AK_Secret", config_parameter='galaxy.aliyun.access.key.secret')

    aliyun_sms_endpoint = fields.Char(
        string="Endpoint", config_parameter='galaxy.aliyun.sms.endpoint')

    enable_aliyun_oss = fields.Boolean("启用OSS存储")
    aliyun_oss_region_id = fields.Char(
        string="地域", config_parameter='galaxy.aliyun.oss.region.id')
    aliyun_oss_public_bucket = fields.Char(
        string="公共读Bucket", config_parameter='galaxy.aliyun.oss.public.bucket')
    aliyun_oss_public_endpoint = fields.Char(
        string="公共读Endpoint", config_parameter='galaxy.aliyun.oss.public.endpoint')
    aliyun_oss_public_endpoint_internal = fields.Char(
        string="内网公共读Endpoint", config_parameter='galaxy.aliyun.oss.public.endpoint.internal')
    aliyun_oss_bucket = fields.Char(
        string="Bucket", config_parameter='galaxy.aliyun.oss.bucket')
    aliyun_oss_endpoint = fields.Char(
        string="Endpoint", config_parameter='galaxy.aliyun.oss.endpoint')
    aliyun_oss_endpoint_internal = fields.Char(
        string="Endpoint", config_parameter='galaxy.aliyun.oss.endpoint.internal')
    aliyun_oss_role_arn = fields.Char(
        string="ARN", config_parameter='galaxy.aliyun.oss.role.arn')
    aliyun_oss_max_per_batch = fields.Char(
        string="批传最大数量", config_parameter='galaxy.aliyun.oss.max.perbatch')
    
    aliyun_vod_region_id = fields.Char(
        string="视频地域", config_parameter='galaxy.aliyun.vod.region.id')
    aliyun_vod_bucket = fields.Char(
        string="Vod Bucket", config_parameter='galaxy.aliyun.vod.bucket')
    aliyun_vod_endpoint = fields.Char(
        string="VodEndpoint", config_parameter='galaxy.aliyun.vod.endpoint')
    
    aliyun_market_app_key = fields.Char(
        string="AppKey", config_parameter='galaxy.aliyun.market.app.key')
    aliyun_market_app_secret = fields.Char(
        string="密钥", config_parameter='galaxy.aliyun.market.app.secret')
    aliyun_market_app_code = fields.Char(
        string="AppCode", config_parameter='galaxy.aliyun.market.app.code')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        if self.env['ir.config_parameter'].get_param('ir_attachment.location', 'file') == 'oss':
            res['enable_aliyun_oss'] = True
        else:
            res['enable_aliyun_oss'] = False

        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].set_param(
            'ir_attachment.location', 'oss' if self.enable_aliyun_oss else 'file')
