# -*- coding: utf-8 -*-


import logging

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InclusiveFinancingContractInforSignToken(models.TransientModel):
    _name = 'ifs.contract.info.sign.token'
    _description = '合同签名入口的临时Token'
    _inherit = ['uuid.short.mixin']
    _order = "create_date desc"
    _transient_max_hours = 840

    contract_info_ids = fields.Many2many(
        'ifs.contract.info', 'ifs_contract_info_token_rel', 'token_id', 'contract_info_id', auto_join=True, string='此次签约的合同')

    sign_name = fields.Char('签名人')
    sign_idcard = fields.Char('签名人身份证号')
    user_id = fields.Many2one('res.users', string='操作用户', ondelete='cascade')
    sign_partner = fields.Reference(
        selection=[], string='签署方', ondelete='restrict')
    sign_company_name = fields.Char('签署公司')
    token = fields.Char(copy=False)
    token_type = fields.Selection([
        ('partner_one', '甲方'),
        ('partner_two', '乙方'),
        ('partner_three', '丙方'),
        ('partner_four', '丁方')
    ], string='签名方', copy=False)
    next_state = fields.Selection([
        ('draft', '草稿'),
        ('unconfirmed', '待确认'),
        ('confirmed', '已确认'),
        ('signed', '已签署'),
        ('abolished', '已作废'),
    ], string='签署后的状态', copy=False, default='confirmed')
    ref_object = fields.Reference(
        selection=[], string='签署后回调的模型', ondelete='set null')
    need_faceid = fields.Boolean('是否需要人脸核身', default=True)
    need_sms_verify = fields.Boolean('短信验证', default=False)
    liveness_video = fields.Binary('人脸核身视频')
    best_frame = fields.Binary('人脸核身截图')
    expiration = fields.Datetime(copy=False)
    token_valid = fields.Boolean(
        compute='_compute_token_valid', string='签名Token是否有效')
    website_id = fields.Many2one(
        "website", string="收单网站", ondelete="restrict", required=True)
    sign_url = fields.Char(
        '手写签名地址', compute='_compute_sign_url')
    is_sync = fields.Boolean("是否异步",default=False)
    sync_state  = fields.Selection([
        ('user_sign', '用户已签'),
        ('committed', '已提交'),
    ],string="是否已签约")
    

    @api.depends('token', 'expiration')
    def _compute_token_valid(self):
        dt = fields.Datetime.now()
        for sign_token in self:
            sign_token.token_valid = bool(sign_token.token) and \
                (not sign_token.expiration or dt <= sign_token.expiration)

    @api.depends('token')
    def _compute_sign_url(self):
        for sign_token in self:
            sign_token.sign_url = ''.join([
                sign_token.website_id.domain,
                '/contract/sign?token=',
                sign_token.token
            ])

    @api.model
    def create(self, vals):
        if 'token' not in vals:
            token = self.short_uuid4()
            while self.sign_with_token(token):
                token = self.short_uuid4()
            vals['token'] = token

        vals['expiration'] = fields.Datetime.now() + timedelta(days=30)
        sign_token = super(
            InclusiveFinancingContractInforSignToken, self).create(vals)

        return sign_token

    def prepare_sign(
            self, contract_info_ids, website_id, sign_name=False, sign_partner=False, idcard=False,
            token_type='partner_one', next_state='confirmed', ref_object=False, need_faceid=False,is_sync=False, need_sms_verify=False):
        sign_token = self.search([
            ('contract_info_ids', 'in', contract_info_ids),
            ('token_type', '=', token_type)
        ])
        sign_token.unlink()
        
        cfg = self.env['ir.config_parameter'].sudo()
        global_disable_faceid = cfg.get_param('ifs.contract.global.disable.faceid', False)
        contract_infos = self.env['ifs.contract.info'].browse(contract_info_ids)
        need_sms_verify = need_sms_verify or contract_infos.is_need_sms_verify()
        if global_disable_faceid:
            need_faceid = False
        else:
            need_faceid = need_faceid or contract_infos.is_need_faceid()
        
        if not idcard and sign_partner._name == 'ifs.gar.entry.merchant':
            idcard = sign_partner.legal_id_number if sign_partner.is_self_guarantee else sign_partner.guarantor_idcard_no
        if not sign_name and sign_partner._name == 'ifs.gar.entry.merchant':
            sign_name = sign_partner.legal_name if sign_partner.is_self_guarantee else sign_partner.guarantor_name
        return self.create({
            'contract_info_ids': [fields.Command.set(contract_info_ids)],
            'token_type': token_type,
            'need_faceid': need_faceid,
            'need_sms_verify': need_sms_verify,
            'website_id': website_id,
            'user_id': self.env.user.id,
            'sign_name': sign_name,
            'sign_idcard': idcard,
            'sign_partner': '%s,%d' % (sign_partner._name, sign_partner.id) if sign_partner else False,
            'sign_company_name': sign_partner.name if sign_partner else False,
            'next_state': next_state,
            'ref_object': '%s,%d' % (ref_object._name, ref_object.id) if ref_object else False,
            'is_sync':is_sync
        })

    def sign_with_token(self, token, check_validity=False, raise_exception=False):
        sign_token = self.search([('token', '=', token)], limit=1)
        if not sign_token:
            if raise_exception:
                raise UserError(_("签名参数无效"))
            return False
        if check_validity and not sign_token.token_valid:
            if raise_exception:
                raise UserError(_("签名Token过期"))
            return False
        return sign_token
