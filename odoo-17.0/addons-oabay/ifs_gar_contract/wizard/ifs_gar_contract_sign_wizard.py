# -*- coding: utf-8 -*-

import base64
import io
from platform import release
import qrcode
from functools import reduce
from datetime import datetime

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GuaranteeAccountsRecvContractSign(models.TransientModel):
    _name = 'ifs.gar.contract.sign.wizard'
    _description = '合同批量签名的向导页'
    _order = 'create_date'
    
    @api.model
    def default_get(self, default_fields):
        default_values = super(GuaranteeAccountsRecvContractSign, self).default_get(default_fields)
        
        # if 'sign_token_id' in default_values:
        #     default_values['contract_info_ids'] = [247, 248, 249, 250]
        
        return default_values

    sign_token_id = fields.Many2one(
        'ifs.contract.info.sign.token',
        string='签约Token', index=True)
    sign_url = fields.Char('手写签名地址')
    sign_qrcode = fields.Image(
        compute='_compute_sign_qrcode', string='手写签名入口二维码')

    contract_info_ids = fields.Many2many('ifs.contract.info', related='sign_token_id.contract_info_ids', string='签约的合同')

    @api.depends('sign_url')
    def _compute_sign_qrcode(self):
        for sign_token in self:
            byte = io.BytesIO()
            qr_img = qrcode.make(data=sign_token.sign_url)
            qr_img.save(byte, 'jpeg')
            sign_token.sign_qrcode = base64.encodebytes(
                byte.getvalue())


class TradeOrderSupplierContractSign(models.TransientModel):
    _name = 'trade.order.supplier.sign.wizard'
    _inherit = 'ifs.gar.contract.sign.wizard'
    _description = '合同批量签名的向导页'
    _order = 'create_date'
    
    
    # trade_order_id =fields.Many2one('ifs.gar.trade.order')
    # trade_order_code =fields.Char(related='trade_order_id.code')
    # trade_order_create_date = fields.Datetime(related='trade_order_id.create_date')
    # supplier_name = fields.Char(related='trade_order_id.supplier_id.name')
    # merchant_name = fields.Char(related='trade_order_id.merchant_id.name')
    # order_code = fields.Char("基础合同编号",related='trade_order_id.order_code')
    # trade_date = fields.Datetime('基础合同签订时间',related='trade_order_id.trade_date')
    # withdrawal_amount= fields.Monetary("本次提款金额",related='trade_order_id.withdrawal_amount')
    # withdrawal_amount_uppercase = fields.Char("请款金额大写",related='trade_order_id.withdrawal_amount_uppercase')
    # payment_days = fields.Integer("账期",related='trade_order_id.payment_days')
    # repayment_date = fields.Datetime("费用承担到期日",related='trade_order_id.repayment_date')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        required=True, default=lambda self: self.env.user.company_id.currency_id)
    
    # item_ids = fields.One2many(
    #     'ifs.gar.trade.order.item', 'trade_order_id', string='订单明细',related='trade_order_id.item_ids')
    
        
    def _rmb_upper(self, value):
        """
            人民币大写
            传入浮点类型的值返回 unicode 字符串
            """
        map = [u"零", u"壹", u"贰", u"叁", u"肆", u"伍", u"陆", u"柒", u"捌", u"玖"]
        unit = [u"分", u"角", u"元", u"拾", u"百", u"千", u"万", u"拾", u"百", u"千", u"亿",
                u"拾", u"百", u"千", u"万", u"拾", u"百", u"千", u"兆"]

        nums = []  # 取出每一位数字，整数用字符方式转换避大数出现误差
        for i in range(len(unit)-3, -3, -1):
            if value >= 10**i or i < 1:
                nums.append(int(round(value/(10**i), 2)) % 10)

        words = []
        zflag = 0  # 标记连续0次数，以删除万字，或适时插入零字
        start = len(nums)-3
        for i in range(start, -3, -1):  # 使i对应实际位数，负数为角分
            if 0 != nums[start-i] or len(words) == 0:
                if zflag:
                    words.append(map[0])
                    zflag = 0
                words.append(map[nums[start-i]])
                words.append(unit[i+2])
            elif 0 == i or (0 == i % 4 and zflag < 3):  # 控制‘万/元’
                words.append(unit[i+2])
                zflag = 0
            else:
                zflag += 1

        if words[-1] != unit[0]:  # 结尾非‘分’补整字
            words.append(u"整")
        return ''.join(words)

    