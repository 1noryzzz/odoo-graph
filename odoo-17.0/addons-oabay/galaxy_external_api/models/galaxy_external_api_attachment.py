# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class ResCompanyBusinessDocument(models.Model):
    _name = 'galaxy.external.api.attachment'
    _description = '接口测试用的附件'

    api_id = fields.Many2one(
        'galaxy.external.api', string='API名称', index=True, ondelete='cascade')
    name = fields.Char('文件名称', required=True)
    attachment = fields.Binary(required=True)
