# -*- coding: utf-8 -*-

import base64
import io
import qrcode

from datetime import timedelta

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class InclusiveFinancingUpdateSupplierSign(models.TransientModel):
    _name = 'ifs.partner.supplier.sign.wizard'
    _description = '供应方存留签名的向导类'
    _order = 'create_date'

    supplier_id = fields.Many2one(
        'ifs.partner.supplier',
        string='供应方', index=True, ondelete='restrict')
    sign_url = fields.Char('手写签名地址')
    sign_qrcode = fields.Image(
        compute='_compute_sign_qrcode', string='手写签名入口二维码')

    @api.depends('sign_url')
    def _compute_sign_qrcode(self):
        for sign_token in self:
            byte = io.BytesIO()
            qr_img = qrcode.make(data=sign_token.sign_url)
            qr_img.save(byte, 'jpeg')
            sign_token.sign_qrcode = base64.encodebytes(
                byte.getvalue())
