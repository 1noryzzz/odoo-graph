# -*- coding: utf-8 -*-

from . import openapi
# -*- coding: utf-8 -*-

import logging
import json
import datetime
import base64
import werkzeug
import qrcode
import calendar
import requests
import hashlib
from functools import reduce
from cache_base import retrieve_cache_base
import random
import string
from urllib.parse import urlencode
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from odoo.http import Controller, request, route
from odoo import _, fields, http
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.galaxy_common.fields import local_to_utc
from tencentcloud.common import credential
from tencentcloud.faceid.v20180301 import faceid_client, models
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.profile.client_profile import ClientProfile
from io import BytesIO

_logger = logging.getLogger(__name__)

payment_order_fields = ['merchant_code', 'pay_amount', 'after_payment', 'url_type']
trade_list_fields = ['supplier_code',
                     'trade_code', 'trade_amount', 'trade_date']

payment_order_fields_change = ['payment_code',
                               'merchant_code', 'pay_amount', 'operate']
trade_list_fields_change = ['trade_code', 'reduce_amount']

payment_order_fields_receipt = ['payment_code', 'merchant_code', 'pay_amount']
trade_list_fields_receipt = [
    'trade_code', 'trade_amount', 'own_trans', 'receipted_order', 'canceled']


class OpenApiController(Controller):
    _WECHAT_AGENT = ['MicroMessenger', 'WeChat', 'wechatdevtools']
    _MOBILE_AGENT = ['Android', 'iPhone', 'iPad', 'iPod', 'Windows Phone', 'MQQBrowser']
    _MINI_AGENT = ['miniProgram']
    
    def determine_the_source(self):
        user_agent = request.httprequest.headers.get('User-Agent')
        open_source = False
        if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MINI_AGENT]):
            open_source = 'wx_mini'
        elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
            open_source = 'wechat'
        elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
            open_source = 'phone'
        else:
            open_source = 'pc'
            
        return open_source

    # 测试 生成采购方apikey
    @route(['/openapi/test/create_apikey'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def create_apikey(self, merchant_code, supplier_code):
        merchant = request.env['ifs.partner.merchant'].search(
            [('seq_code', '=', merchant_code)])
        supplier = request.env['ifs.partner.supplier'].search(
            [('seq_code', '=', supplier_code)])
        api_app = request.env['galaxy.open.api.app'].sudo().search(
            [('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用Owner！'))
        apikey = request.env["res.users.apikeys"].with_user(
            merchant.root_employee_id.sudo().user_id)._generate('galaxy.open.api', api_app.app_id)
        return apikey

    @route(['/openapi/payment/cashier'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def to_cashier_page(self, payment_code, token):
        try:
            payment_order = self.search_payment_order_info(payment_code, token)
        except UserError as err:
            _logger.error(repr(err))
            
            return request.render('ifs_gar_trade.err_page', {
                'is_success': False,
                'alert_msg': err.args[0]
            })
        
        open_source = self.determine_the_source()

        return request.render(
            'ifs_gar_trade.ifs_gar_trade_mobile_cashier_template',
            {
                'is_error': False,
                'unable_list': [],
                "payment_code": payment_code,
                "merchant_code": payment_order.merchant_code,
                'amount': payment_order.pay_amount,
                'open_source': open_source
            }
        )

    @route(['/openapi/payment/verify_password'], type='json', auth="public", cors="*", methods=['POST'], website=True)
    def verify_password(self, password, merchant_code):
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', merchant_code)])
        if password != merchant.payment_password:
            return {
                'is_success': False,
                'msg': '支付密码错误'
            }

        return {
            'is_success': True,
            'msg': '验证成功'
        }

    @route(['/openapi/payment/result'], type='json', auth="public", cors="*", methods=['POST'], website=True)
    def to_pay_result_page(self, payment_code):
        try:
            payment_order = self.search_payment_order_info(payment_code)
        except UserError as err:
            _logger.error(repr(err))
            
            return {
                'is_success': False,
                'alert_msg': err.args[0]
            }
        url_type = payment_order.url_type
        after_payment = payment_order.after_payment + (payment_code if url_type == 'wxmini' else '')
        
        try:
            payment_order.freeze_order()
        except Exception as e:
            _logger.error(repr(e))
            after_payment = after_payment + (
                '&isSuccess=false&msg=支付失败' if url_type == 'wxmini' else (
                    '&isSuccess=false&msg=支付失败' if ('?' in after_payment) else '?isSuccess=false&msg=支付失败'))
            request.env.cr.rollback()
            return {
                'after_payment': after_payment,
                'url_type': url_type
            }

        supplier_code = payment_order.trade_list[0].supplier_code
        supplier = request.env['ifs.partner.supplier'].sudo().search(
            [('seq_code', '=', supplier_code)])
        api_app = request.env['galaxy.open.api.app'].sudo().search(
            [('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], order='create_date desc', limit=1)
        if not api_app:
            return {
                'is_success': False,
                'alert_msg': '没有找到对应的应用,请联系管理人员'
            }
        
        message_body = {
            'payment_info': {
                'payment_code': payment_order.seq_code,
                'merchant_code': payment_order.merchant_code,
                'pay_amount': payment_order.pay_amount,
                'state': payment_order.state,
                'approved_quota': payment_order.bill_id.sub_loan_account_id.approved_quota,
                'available_quota': payment_order.bill_id.sub_loan_account_id.available_quota,
            },
            'trade_list': [
                {
                    'trade_code': trade.trade_code,
                    'trade_amount': trade.trade_amount,
                    'reduce_amount': trade.reduce_amount,
                    'state': trade.state,
                    'bill_code': trade.bill_id.code,
                    'operate_type': trade.bill_log_id.operate_type,
                    'start_bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date)),
                    'bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date)),
                    'repayment_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date)),
                } for trade in payment_order.trade_list
            ]
        }
        request.env['ifs.message'].sudo().trigger_push(
            api_app, 'pay', message_body)

        pay_amount = payment_order.pay_amount and int(payment_order.pay_amount)
        after_payment = after_payment + (
            f'&isSuccess=true&msg=支付完成&payAmount={pay_amount}' if url_type == 'wxmini' else (
                f'&isSuccess=true&msg=支付完成&payAmount={pay_amount}' if ('?' in after_payment) else f'?isSuccess=true&msg=支付完成&payAmount={pay_amount}'))
        return {
            'after_payment': after_payment,
            'url_type': url_type
        }
    
    @route(['/openapi/merchant/chpwd/tips'], type='json', auth="public", cors="*", methods=['POST'], website=True)
    def chpwd_tips(self, merchant_code):  
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', merchant_code)], limit=1)
        if not merchant:
            return {
                'is_success': False,
                'alert_msg': '商户不存在'
            }
        
        try:
            res = self.change_pwd(
                merchant_code, merchant.root_employee_id.identification_id)
        except UserError as err:
            _logger.error(repr(err))
            
            return {
                'is_success': False,
                'alert_msg': err.args[0]
            }

        url = request.httprequest.host_url + \
            'openapi/payment/inform?token=' + res.get('token')
        return {
            'is_success': True,
            'change_url': url
        }
        
    def search_payment_order_info(self, payment_code, token=False):
        payment_order = request.env['ifs.gar.payment.order'].sudo().search(
            [('seq_code', '=', payment_code)], limit=1)
        
        if not payment_order.exists():
            raise UserError(_('不存在该订单'))
        if not payment_order.token_valid:
            raise UserError(_('token已过期'))
        if token and payment_order.token != token:
            raise UserError(_('token无效'))
        if payment_order.state != "draft":
            raise UserError(_('该订单已支付'))
        
        return payment_order

    @route(['/openapi/merchant/change_pwd'], type='json', auth="openapi", cors="*", methods=['POST'], website=True)
    def change_pwd(self, merchant_code, id_card_no):
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', merchant_code)], limit=1)
        if not merchant.exists():
            raise UserError(_("商户不存在"))
        if merchant.root_employee_id.identification_id != id_card_no:
            raise UserError(_("身份证号不匹配"))

        change_password_temp_token = request.env['ifs.gar.change.password.temp.token'].sudo().create({
            'merchant_code': merchant.seq_code,
        })

        return {
            'merchant_code': change_password_temp_token.merchant_code,
            'token': change_password_temp_token.token
        }

    @route(['/openapi/merchant/generate/qrcode'], type='json', auth="public", cors="*", methods=['POST'], website=True)
    def generate_qrcode(self, token):
        try:
            self.get_chpwd_token_model(token)
        except UserError as err:
            _logger.error(repr(err))
            
            return {
                'is_success': False,
                'alert_msg': err.args[0]
            }
        
        url = request.httprequest.host_url + 'openapi/payment/inform?token=' + token
        # 将生成的链接变成二维码
        qr = qrcode.QRCode(
            version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # 将最后的图片转成base64字符串
        buf = BytesIO()
        img.save(buf, format='PNG')
        qr_image = base64.b64encode(buf.getvalue())

        return {
            'is_success': True,
            'qrCodeSrc': qr_image.decode()
        }
        
    @route(['/openapi/page/error'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def to_error_page(self, err_msg):            
        return request.render('ifs_gar_trade.err_page', {
            'is_success': False,
            'alert_msg': err_msg
        })

    @route(['/openapi/payment/inform'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def inform(self, token):
        try:
            chpwd_token_model = self.get_chpwd_token_model(token)
        except UserError as err:
            _logger.error(repr(err))
            
            return request.render('ifs_gar_trade.err_page', {
                'is_success': False,
                'alert_msg': err.args[0]
            })
            
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', chpwd_token_model.merchant_code)], limit=1)

        return request.render('ifs_gar_trade.ifs_gar_trade_mobile_inform_template', {
            'merchant_code': chpwd_token_model.merchant_code,
            'name': merchant.root_employee_id.name,
            'token': token
        })

    # h5快捷进件-人脸识别
    @route('/openapi/payment/ocr/matchFace', auth="public", type="http", methods=['GET'], website=True, csrf=False)
    def bd_matchFace(self, token):
        try:
            chpwd_token_model = self.get_chpwd_token_model(token)
        except UserError as err:
            _logger.error(repr(err))
            
            return request.render('ifs_gar_trade.err_page', {
                'is_success': False,
                'alert_msg': err.args[0]
            })
        
        user_agent = request.httprequest.headers.get('User-Agent')
        
        merchant_code = chpwd_token_model.merchant_code
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', merchant_code)], limit=1)

        Config = request.env['ir.config_parameter'].sudo()
        need_faceid = Config.get_param(
            'ifs.contract.global.disable.faceid', False)
        if not need_faceid:
            sign_idcard = merchant.root_employee_id.identification_id
            sign_name = merchant.root_employee_id.name
            if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
                client = self._prepare_client()
                req = models.DetectAuthRequest()
                params = {
                    "IdCard": merchant.root_employee_id.identification_id,
                    "Name": merchant.root_employee_id.name,
                    "RedirectUrl": f"{http.request.httprequest.host_url}/openapi/merchant/chpwd?token={token}",
                    "RuleId": "1",
                }
                req.from_json_string(json.dumps(params))
                resp = client.DetectAuth(req)

                return werkzeug.utils.redirect(resp.Url)
            elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
                # TODO: 移动端人脸核身
                RedirectUrl = "%s/openapi/merchant/chpwd?token=%s" % (request.website.domain, token)
                full_url = self.upload_identity_info(f'userId_{sign_idcard}', sign_name, sign_idcard, RedirectUrl)
                return werkzeug.utils.redirect(full_url)
                
            else:
                # TODO: PC端人脸核身
                RedirectUrl = "%s/openapi/merchant/chpwd?token=%s" % (request.website.domain, token)
                full_url = self.geth5faceid(f'userId_{sign_idcard}', sign_name, sign_idcard, RedirectUrl)
                return werkzeug.utils.redirect(full_url)
        else:
            return request.redirect(f'/openapi/merchant/chpwd?token={token}')

    @route(['/openapi/merchant/chpwd'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def to_set_payment_password_page(self, token, **kw):
        try:
            self.get_chpwd_token_model(token)
        except UserError as err:
            _logger.error(repr(err))
            
            return request.render('ifs_gar_trade.err_page', {
                'is_success': False,
                'alert_msg': err.args[0]
            })
        
        user_agent = request.httprequest.headers.get('User-Agent')
        Config = request.env['ir.config_parameter'].sudo()
        need_faceid = Config.get_param(
            'ifs.contract.global.disable.faceid', False)
        
        if False: #not need_faceid:
            if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
                if not kw.get('BizToken'):
                    return werkzeug.utils.redirect("%s/openapi/payment/ocr/matchFace?token=%s" % (request.website.domain, token))
                client = self._prepare_client()
                req = models.GetDetectInfoEnhancedRequest()
                params = {
                    "BizToken": kw.get('BizToken', ''),
                    "RuleId": "1"
                }
                req.from_json_string(json.dumps(params))
                resp = client.GetDetectInfoEnhanced(req)
                if resp.Text.ErrCode == 0:
                    return request.render('ifs_gar_trade.ifs_gar_trade_mobile_set_payment_password_template')
                else:
                    return request.render(
                        'ifs_gar_trade.payment_match_face_error_msg_page', {
                            'token': token,
                            'alert_msg': resp.Text.ErrMsg
                        })
            elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
                if not kw.get('orderNo') or not kw.get('h5faceId'):
                    return werkzeug.utils.redirect("%s/openapi/payment/ocr/matchFace?token=%s" % (request.website.domain, token))
                # 查询核身结果
                orderNo = kw.get('orderNo')
                resp = self.queryfacerecord(orderNo)
                if resp.status_code != 200:
                    return request.render(
                        'ifs_gar_trade.payment_match_face_error_msg_page', {
                            'token': token,
                            'alert_msg': '获取认证结果失败'
                        })
                resp_data = resp.json()
                if resp_data.get('code') != '0':
                    return request.render(
                        'ifs_gar_trade.payment_match_face_error_msg_page', {
                            'token': token,
                            'alert_msg': resp_data.get('msg')
                        })
                return request.render('ifs_gar_trade.ifs_gar_trade_mobile_set_payment_password_template')
            else:
                if not kw.get('orderNo') or not kw.get('h5faceId'):
                    return werkzeug.utils.redirect("%s/openapi/payment/ocr/matchFace?token=%s" % (request.website.domain, token))
                # 查询核身结果
                orderNo = kw.get('orderNo')
                resp = self.queryfacerecord(orderNo)
                if resp.status_code != 200:
                    return request.render(
                        'ifs_gar_trade.payment_match_face_error_msg_page', {
                            'token': token,
                            'alert_msg': '获取认证结果失败'
                        })
                resp_data = resp.json()
                if resp_data.get('code') != '0':
                    return request.render(
                        'ifs_gar_trade.payment_match_face_error_msg_page', {
                            'token': token,
                            'alert_msg': resp_data.get('msg')
                        })
                return request.render('ifs_gar_trade.ifs_gar_trade_mobile_set_payment_password_template')
        else:
            cache_base = retrieve_cache_base(request.env, 'TOKEN-CACHE')
            with cache_base.redis_db.connection_open() as db:
                sms_verified = db.get(f'ifs_gar_chpwd_sms_verified_{token}')

            if sms_verified:
                return request.render('ifs_gar_trade.ifs_gar_trade_mobile_set_payment_password_template')

            chpwd_token_model = self.get_chpwd_token_model(token)
            merchant = request.env['ifs.partner.merchant'].sudo().search(
                [('seq_code', '=', chpwd_token_model.merchant_code)], limit=1)
            if not merchant or not merchant.root_employee_id.mobile_phone:
                return request.render('ifs_gar_trade.err_page', {
                    'is_success': False,
                    'alert_msg': '无法获取商户手机号，请联系管理员'
                })

            mobile = merchant.root_employee_id.mobile_phone
            self._send_chpwd_sms_code(mobile)
            masked_mobile = mobile[:3] + '****' + mobile[-4:]
            return request.render('ifs_gar_trade.ifs_gar_trade_mobile_sms_verify_template', {
                'token': token,
                'masked_mobile': masked_mobile,
            })

    def _get_or_create_chpwd_sms_record(self, mobile):
        sudo = request.env['ifs.gar.chpwd.sms.code'].sudo()
        record = sudo.search([('mobile', '=', mobile)], limit=1)
        if not record:
            record = sudo.create({'mobile': mobile})
        return record

    def _send_chpwd_sms_code(self, mobile):
        record = self._get_or_create_chpwd_sms_record(mobile)
        record.generate_verification_code(mobile)
        record.send_verification_code(mobile)

    @route(['/openapi/merchant/chpwd/send_sms'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def send_chpwd_sms(self, token):
        try:
            chpwd_token_model = self.get_chpwd_token_model(token)
        except UserError as err:
            return request.make_response(
                json.dumps({'success': False, 'msg': err.args[0]}),
                headers=[('Content-Type', 'application/json')]
            )

        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', chpwd_token_model.merchant_code)], limit=1)
        if not merchant or not merchant.root_employee_id.mobile_phone:
            return request.make_response(
                json.dumps({'success': False, 'msg': '无法获取商户手机号'}),
                headers=[('Content-Type', 'application/json')]
            )

        mobile = merchant.root_employee_id.mobile_phone
        try:
            self._send_chpwd_sms_code(mobile)
        except Exception as e:
            _logger.error(repr(e))
            return request.make_response(
                json.dumps({'success': False, 'msg': '发送失败，请稍后再试'}),
                headers=[('Content-Type', 'application/json')]
            )

        return request.make_response(
            json.dumps({'success': True}),
            headers=[('Content-Type', 'application/json')]
        )

    @route(['/openapi/merchant/chpwd/verify_sms'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def verify_chpwd_sms(self, token, code):
        try:
            chpwd_token_model = self.get_chpwd_token_model(token)
        except UserError as err:
            return request.make_response(
                json.dumps({'success': False, 'msg': err.args[0]}),
                headers=[('Content-Type', 'application/json')]
            )

        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', chpwd_token_model.merchant_code)], limit=1)
        if not merchant or not merchant.root_employee_id.mobile_phone:
            return request.make_response(
                json.dumps({'success': False, 'msg': '无法获取商户手机号'}),
                headers=[('Content-Type', 'application/json')]
            )

        mobile = merchant.root_employee_id.mobile_phone
        sms_code_model = request.env['ifs.gar.chpwd.sms.code'].sudo()
        verified = sms_code_model.check_verification_code(mobile, code)

        if verified:
            cache_base = retrieve_cache_base(request.env, 'TOKEN-CACHE')
            with cache_base.redis_db.connection_open() as db:
                db.setex(name=f'ifs_gar_chpwd_sms_verified_{token}', value='1', time=5 * 60)
            return request.make_response(
                json.dumps({'success': True}),
                headers=[('Content-Type', 'application/json')]
            )

        return request.make_response(
            json.dumps({'success': False, 'msg': '验证码错误'}),
            headers=[('Content-Type', 'application/json')]
        )

    @route(['/openapi/payment/set_password'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def set_payment_password(self, token, password):
        try:
            chpwd_token_model = self.get_chpwd_token_model(token)
        except UserError as err:
            _logger.error(repr(err))
            
            return request.render('ifs_gar_trade.err_page', {
                'is_success': False,
                'alert_msg': err.args[0]
            })
        
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', chpwd_token_model.merchant_code)], limit=1)
        if not merchant:
            return request.render('ifs_gar_trade.chpwd_result_msg_page', {
                'is_success': False,
                'alert_msg': '未找到采购方',
            })
        merchant.write({
            'payment_password': password
        })

        chpwd_token_model.unlink()
        return request.redirect(merchant.generate_sign_url())

        # return request.render('ifs_gar_trade.chpwd_result_msg_page', {
        #     'is_success': True,
        #     'alert_msg': '修改成功',
        # })

    def get_chpwd_token_model(self, token):
        chpwd_token_model = request.env['ifs.gar.change.password.temp.token'].sudo(
            ).search([('token', '=', token)], limit=1)

        if not chpwd_token_model.exists():
            raise UserError("token无效")
        if not chpwd_token_model.token_valid:
            raise UserError("token已过期")

        return chpwd_token_model
        
    @route(['/openapi/bill/retrieve_temp_token'], type='json', auth="openapi", cors="*", methods=['POST'], website=True)
    def bill_retrieve_temp_token(self, merchant_code):
        merchant = request.env['ifs.partner.merchant'].search(
            [('seq_code', '=', merchant_code)], limit=1)
        if not merchant.exists():
            raise UserError(_("商户不存在"))
        supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
        loan_account = request.env['ifs.gar.sub.loan.account'].sudo().search([('supplier_id', '=', supplier.id), ('merchant_id', '=', merchant.id)])

        bill_retrieve_temp_token = request.env['ifs.gar.bill.retrieve.temp.token'].sudo().create({
            'loan_account_id': loan_account.id,
            'merchant_code': merchant.seq_code
        })

        return {
            'merchant_code': bill_retrieve_temp_token.merchant_code,
            'token': bill_retrieve_temp_token.token
        }
        
    @route(['/openapi/bill/bill_info'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def bill_info(self, merchant_code, token):
        bill_retrieve_temp_token = self.get_bill_retrieve_temp_token(token)
        br_merchant_code = bill_retrieve_temp_token.merchant_code
        if br_merchant_code != merchant_code:
            raise UserError(_("商编号有误"))
        
        loan_account = bill_retrieve_temp_token.loan_account_id
        now = datetime.datetime.now()
        code = ''.join([str(now.year), '%02d' % now.month])
        loan_account_bill = request.env['ifs.gar.loan.account.bill'].sudo().search([('sub_loan_account_id', '=', loan_account.id), ('code', '=', code)])
        current_bill_refund_trade_list = request.env['ifs.gar.trade.list'].sudo().search([('bill_id', '=', loan_account_bill.id), ('state', '=', 'refund')])
        current_total_reduce_amount = sum([refund_trade.reduce_amount for refund_trade in current_bill_refund_trade_list])
        
        return request.render('ifs_gar_trade.ifs_gar_trade_mobile_my_bill_template', {
            'total_repaid_amount': (loan_account.approved_quota - loan_account.available_quota) / 100,
            'approved_quota': loan_account.approved_quota / 100,
            'available_quota': loan_account.available_quota / 100,
            'current_used_amount': (loan_account_bill.freeze_quota + loan_account_bill.used_quota) / 100,
            'current_repaid_amount': (loan_account_bill.freeze_quota + loan_account_bill.used_quota + current_total_reduce_amount) / 100,
            'current_total_reduce_amount': current_total_reduce_amount / 100,
            'bill_date': 1,
            'bill_issued_list': [{
                'bill_id': bill.id,
                'bill_date': bill.start_bill_date and '-'.join([str(bill.start_bill_date.year),'%02d' % bill.start_bill_date.month]),
                'state': bill.state,
                'state_text': dict(bill._fields['state'].selection).get(bill.state),
                'repayment_date': (bill.repayment_date - timedelta(days=1)).strftime('%Y-%m-%d'),
                'bill_amount': bill.bill_amount / 100,
                'pending_repayment': (bill.bill_amount + bill.pending_interest + bill.pending_damages - bill.repayment_amount) if bill.state == 'overdue' else bill.bill_amount,
                } for bill in loan_account.bill_ids
            ]
        })
    
    @route(['/openapi/bill/bill_info_details'], type='http', auth="public", cors="*", methods=['GET'], website=True)
    def bill_info_details(self, bill_id):
        loan_account = request.env['ifs.gar.loan.account.bill'].sudo().search([('id', '=', bill_id)], limit=1)
        trade_list = request.env['ifs.gar.trade.list'].sudo().search([('bill_id', '=', int(bill_id))])
        bill_total_reduce_amount = sum([filtered_trade.reduce_amount for filtered_trade in trade_list.filtered(lambda trade: trade.state == 'refund')])

        return request.render('ifs_gar_trade.ifs_gar_trade_mobile_bill_details_template', {
            'used_quota': loan_account.used_quota / 100,
            'bill_total_reduce_amount': bill_total_reduce_amount / 100,
            'repayment_date': loan_account.repayment_date.strftime('%Y-%m-%d'),
            'period_bill_date': '11.01-11.30',
            'repayment_amount': loan_account.repayment_amount,
            'pending_interest': loan_account.pending_interest + loan_account.pending_damages,
            'pending_repayment': (loan_account.bill_amount + loan_account.pending_interest + loan_account.pending_damages - 
                                 loan_account.repayment_amount) if loan_account.state == 'overdue' else loan_account.bill_amount,
            'trade_list': [{
                'trade_code': trade.trade_code,
                'trade_date': trade.trade_date.strftime('%Y-%m-%d'),
                'payment_amount': (trade.trade_amount - trade.reduce_amount) / 100,
                'state_text': dict(trade._fields['state'].selection).get(trade.state)
            } for trade in trade_list]
        })
        
    def get_bill_retrieve_temp_token(self, token):
        bill_retrieve_temp_token = request.env['ifs.gar.bill.retrieve.temp.token'].sudo(
        ).search([('token', '=', token)], limit=1)

        if not bill_retrieve_temp_token.exists():
            raise UserError("token无效")
        if not bill_retrieve_temp_token.token_valid:
            raise UserError("token已过期")

        return bill_retrieve_temp_token

    def _prepare_client(self):
        cfg = request.env['ir.config_parameter'].sudo()
        face_secret_id = cfg.get_param('ifs.contract.face.secret.id', False)
        face_secret_key = cfg.get_param('ifs.contract.face.secret.key', False)
        cred = credential.Credential(
            face_secret_id, face_secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "faceid.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = faceid_client.FaceidClient(cred, "", clientProfile)

        return client

    # 生成支付订单
    @route(['/openapi/payment/create_order'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def create_order(self, payment_info, trade_list):
        # 校验参数必填和数据是否有误
        self.chack_data(payment_info, payment_order_fields)
        if payment_info.get('url_type') not in ['web', 'wxmini']:
            raise UserError('url类型错误！')
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', payment_info.get('merchant_code'))])
        if not merchant:
            raise UserError('付款方商编不存在！')

        if not isinstance(trade_list, list):
            raise UserError('trade_list参数类型错误！')
        for data in trade_list:
            self.chack_data(data, trade_list_fields)
            supplier = request.env['ifs.partner.supplier'].sudo().search(
                [('seq_code', '=', data.get('supplier_code'))])
            if not supplier:
                raise UserError('供应方商编不存在！')
            
            # 校验当前采购方在供应方下的子账户是否正常
            loan_account = request.env['ifs.gar.sub.loan.account'].sudo().search([
                ('supplier_id', '=', supplier.id), ('merchant_id', '=', merchant.id)], limit=1)
            if not loan_account or loan_account.state == 'freeze':
                raise UserError(f'采购方{merchant.seq_code}在供应方{supplier.seq_code}下的账户不存在或已被冻结！')
            
            # 校验交易日期是否正常
            if fields.Date.from_string(data.get('trade_date')) > fields.Date.today():
                raise UserError('交易日期不可超过当前时间！')
        
        # 校验金额数据
        pay_amount = 0
        for trade_order in trade_list:
            pay_amount += trade_order.get('trade_amount')
        if pay_amount != payment_info.get('pay_amount'):
            raise UserError('支付金额必须与交易订单列表中的所有交易金额之和一致！')

        # 校验是否有重复的订单号
        trade_codes = [trade["trade_code"] for trade in trade_list]
        has_duplicates = len(set(trade_codes)) != len(trade_codes)
        if has_duplicates:
            raise UserError('存在重复的交易订单号，不可创建！')

        payment_info.update({
            'merchant_id': merchant.id,
        })
        payment_order = request.env['ifs.gar.payment.order'].sudo().create(
            payment_info)
        payment_order.update({
            'trade_list': [fields.Command.create({
                'supplier_code': trade.get('supplier_code'),
                'supplier_id': supplier.id,
                'trade_code': trade.get('trade_code'),
                'trade_amount': trade.get('trade_amount'),
                'trade_date': fields.Date.from_string(trade.get('trade_date')),
            }) for trade in trade_list]
        })
        return {
            'payment_code': payment_order.seq_code,
            'token': payment_order.token
        }

    # 查询支付订单
    @route(['/openapi/payment/payment_order'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def search_payment_order(self, payment_code):
        payment_order = request.env['ifs.gar.payment.order'].sudo().search(
            [('seq_code', '=', payment_code)])
        if not payment_order:
            raise UserError('支付订单不存在！')
        return {
            'payment_info': {
                'merchant_code': payment_order.merchant_code,
                'pay_amount': payment_order.pay_amount,
                'state': payment_order.state,
                'approved_quota': payment_order.bill_id.sub_loan_account_id.approved_quota,
                'available_quota': payment_order.bill_id.sub_loan_account_id.available_quota,
            },
            'trade_list': [
                {
                    'trade_code': trade.trade_code,
                    'trade_amount': trade.trade_amount,
                    'reduce_amount': trade.reduce_amount,
                    'state': trade.state,
                    'bill_code': trade.bill_id.code,
                    'operate_type': trade.bill_log_id.operate_type,
                    'start_bill_date': fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date),
                    'bill_date': fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date),
                    'repayment_date': fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date),
                } for trade in payment_order.trade_list
            ]
        }

    # 取消或部分取消订单
    @route(['/openapi/payment/change_order'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def change_payment_order(self, payment_info, trade_list):
        # 校验参数必填和数据是否有误
        self.chack_data(payment_info, payment_order_fields_change)
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', payment_info.get('merchant_code'))])
        if not merchant:
            raise UserError('付款方商编不存在！')
        payment_order = request.env['ifs.gar.payment.order'].sudo().search(
            [('seq_code', '=', payment_info.get('payment_code'))])
        if not payment_order:
            raise UserError('支付订单不存在！')
        if payment_order.state in ['draft', 'loan']:
            raise UserError('该支付订单当前状态不可进行取消操作！')

        if payment_info.get('operate') == 'cancel_payment' and payment_info.get('pay_amount') != 0:
            raise UserError('支付订单金额必须为0！')

        if not isinstance(trade_list, list):
            raise UserError('trade_list参数类型错误！')
        for data in trade_list:
            self.chack_data(data, trade_list_fields_change)
            if data['reduce_amount'] != 0 and not (data['reduce_reasons'] and data['reduce_reson_desc']):
                raise UserError('调整理由或调整说明不能为空！')

            # 找到对应的交易订单
            trade_order = payment_order.trade_list.filtered(
                lambda x: x.trade_code == data['trade_code'])
            if not trade_order:
                raise UserError('根据交易订单号%s未找到相应的交易订单！' % data['trade_code'])

            # 校验当前采购方在供应方下的子账户是否正常
            if trade_order.bill_id.sub_loan_account_id.state == 'freeze':
                raise UserError(f'采购方{merchant.seq_code}在供应方{trade_order.supplier_code}下的账户已被冻结！')
            
            if payment_info.get('operate') == 'cancel_payment' and data['reduce_amount'] != trade_order.trade_amount:
                raise UserError('取消订单的调整金额必须等于交易金额！')
            if data['reduce_amount'] >= 0 and trade_order.trade_amount >= data['reduce_amount']:
                # 如果不是全部退款的订单要先将金额解冻
                if not (trade_order.state == 'refund' and trade_order.trade_amount == trade_order.reduce_amount):
                    bill_log = request.env['ifs.gar.loan.account.bill'].sudo().insert_bill(
                        trade_order.bill_id.sub_loan_account_id, trade_order, 'unfreeze', -(trade_order.trade_amount - 
                        trade_order.reduce_amount),
                        remark='交易订单取消，解冻额度', record_bill=trade_order.bill_id, prev_log=trade_order.bill_log_id)
                    trade_order.bill_log_id = bill_log.id
                
                # 调整金额
                if data['reduce_amount'] != 0:
                    reduce_reasons = data['reduce_reasons'].split(',')
                    reasons = request.env['ifs.gar.trade.reduce.reasons'].sudo().search(
                        [('code', 'in', reduce_reasons)])
                    if not reasons:
                        raise UserError('调整理由参数错误！')
                    trade_order.write({
                        'reduce_reson_desc': data['reduce_reson_desc'],
                        'reduce_reasons': [(4, reason.id, False) for reason in reasons]
                    })
                trade_order.write({
                    'reduce_amount': data['reduce_amount'],
                    'state': 'refund' if data['reduce_amount'] != 0 else 'freeze'
                })

                # 再冻结
                if trade_order.trade_amount != trade_order.reduce_amount:
                    bill_log = request.env['ifs.gar.loan.account.bill'].sudo().insert_bill(
                        trade_order.bill_id.sub_loan_account_id, trade_order, 'freeze', trade_order.trade_amount -
                        trade_order.reduce_amount,
                        remark='交易订单提交，冻结额度', record_bill=trade_order.bill_id, prev_log=trade_order.bill_log_id)
                    trade_order.bill_log_id = bill_log.id
            else:
                raise UserError('调整金额不能大于交易金额或小于零！')

        # 校验金额是否正确
        pay_amount = sum(
            trade.trade_amount - trade.reduce_amount for trade in payment_order.trade_list)
        if payment_info.get('pay_amount') != pay_amount:
            raise UserError("付款金额与修改后的交易订单金额总和不匹配！")

        # 判断是否需要发送通知
        is_send = payment_order.pay_amount != pay_amount or pay_amount == 0

        # 消息推送
        message_body = {
            'payment_info': {
                'payment_code': payment_order.seq_code,
                'merchant_code': payment_order.merchant_code,
                'pay_amount': payment_order.pay_amount,
                'state': payment_order.state,
                'approved_quota': payment_order.bill_id.sub_loan_account_id.approved_quota,
                'available_quota': payment_order.bill_id.sub_loan_account_id.available_quota,
            }
        }
        if is_send:
            # 更新支付订单
            payment_order.write({
                'pay_amount': pay_amount,
                'state': 'refund' if pay_amount == 0 else 'part_refund',
            })
            message_body['payment_info'].update({
                'pay_amount': payment_order.pay_amount,
                'state': payment_order.state,
            })
            message_trade_list = [
                {
                    'trade_code': trade.trade_code,
                    'trade_amount': trade.trade_amount,
                    'reduce_amount': trade.reduce_amount,
                    'final_amount': trade.final_amount,
                    'state': trade.state,
                    'bill_code': trade.bill_id.code,
                    'operate_type': trade.bill_log_id.operate_type,
                    'start_bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date)),
                    'bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date)),
                    'repayment_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date)),
                } for trade in payment_order.trade_list
            ]
            supplier_code = payment_order.trade_list[0].supplier_code
            supplier = request.env['ifs.partner.supplier'].sudo().search(
                [('seq_code', '=', supplier_code)])
            api_app = request.env['galaxy.open.api.app'].sudo().search(
                [('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], order='create_date desc', limit=1)
            if not api_app:
                raise UserError(_('没有找到对应的应用！'))
            message_body['trade_list'] = message_trade_list
            request.env['ifs.message'].sudo().trigger_push(
                api_app, 'pay', message_body)

        return_trade_list = [
            {
                'trade_code': trade.trade_code,
                'trade_amount': trade.trade_amount,
                'reduce_amount': trade.reduce_amount,
                'final_amount': trade.final_amount,
                'state': trade.state,
                'bill_code': trade.bill_id.code,
                'operate_type': trade.bill_log_id.operate_type,
                'start_bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date)),
                'bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date)),
                'repayment_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date)),
            } for trade in payment_order.trade_list
        ]
        message_body['trade_list'] = return_trade_list
        return message_body

    # 订单用信确认
    @route(['/openapi/payment/receipt_order'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def receipt_payment_order(self, payment_info, trade_list=False):
        # 校验参数必填和数据是否有误
        self.chack_data(payment_info, payment_order_fields_receipt)
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('seq_code', '=', payment_info.get('merchant_code'))])
        if not merchant:
            raise UserError('付款方商编不存在！')

        payment_order = request.env['ifs.gar.payment.order'].sudo().search(
            [('seq_code', '=', payment_info.get('payment_code'))])
        if not payment_order:
            raise UserError('支付订单不存在！')
        if payment_order.state in ['draft', 'loan', 'refund']:
            raise UserError('该支付订单当前状态不可付款！')

        # 校验金额是否正确
        if payment_info.get('pay_amount') != payment_order.pay_amount:
            raise UserError("付款金额与交易订单金额总和不匹配！")

        if trade_list:
            if not isinstance(trade_list, list):
                raise UserError('trade_list参数类型错误！')
            for data in trade_list:
                self.chack_data(data, trade_list_fields_receipt)
                if not data['canceled'] and not data.get('receipt_code'):
                    raise UserError('物流单号不能为空！')
                # 找到对应的交易订单
                trade_order = payment_order.trade_list.filtered(
                    lambda x: x.trade_code == data['trade_code'])
                if not trade_order:
                    raise UserError('根据交易订单号%s未找到相应的交易订单！' %
                                    data['trade_code'])
                
                # 校验当前采购方在供应方下的子账户是否正常
                if trade_order.bill_id.sub_loan_account_id.state == 'freeze':
                    raise UserError(f'采购方{merchant.seq_code}在供应方{trade_order.supplier_code}下的账户已被冻结！')

                if trade_order.final_amount != data['trade_amount']:
                    raise UserError('交易金额与交易订单金额不一致！')
                if data['canceled'] and trade_order.final_amount > 0:
                    raise UserError('参数错误，交易订单的交易金额不为0， 订单未取消！')
                elif not data['canceled'] and trade_order.final_amount != 0:
                    trade_order.write({
                        'receipt_code': data.get('receipt_code'),
                        'own_trans': data['own_trans'],
                        'receipted_order': data['receipted_order'],
                    })

        uncanceled_order = payment_order.trade_list.filtered(
            lambda x: not x.canceled)
        is_loan = all(order.receipt_code for order in uncanceled_order)
        if is_loan:
            for trade in payment_order.trade_list:
                # 解冻再动支
                unfreeze_bill_log = request.env['ifs.gar.loan.account.bill'].sudo().insert_bill(
                    trade.bill_id.sub_loan_account_id, trade, 'unfreeze', -trade.final_amount,
                    remark='交易已确立，解冻额度', record_bill=trade.bill_id, prev_log=trade.bill_log_id)
                bill_log = request.env['ifs.gar.loan.account.bill'].sudo().insert_bill(
                    trade.bill_id.sub_loan_account_id, trade, 'loan', trade.final_amount,
                    remark='交易确认，使用额度', record_bill=trade.bill_id, prev_log=unfreeze_bill_log)
                trade.bill_log_id = bill_log.id
                trade.state = 'loan'
                payment_order.state = 'loan'
            supplier_code = payment_order.trade_list[0].supplier_code
            supplier = request.env['ifs.partner.supplier'].sudo().search(
                [('seq_code', '=', supplier_code)])
            api_app = request.env['galaxy.open.api.app'].sudo().search(
                [('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], order='create_date desc', limit=1)
            if not api_app:
                raise UserError(_('没有找到对应的应用！'))
            message_body = {
                'payment_info': {
                    'payment_code': payment_order.seq_code,
                    'merchant_code': payment_order.merchant_code,
                    'pay_amount': payment_order.pay_amount,
                    'state': payment_order.state,
                    'approved_quota': payment_order.bill_id.sub_loan_account_id.approved_quota,
                    'available_quota': payment_order.bill_id.sub_loan_account_id.available_quota,
                },
                'trade_list': [
                    {
                        'trade_code': trade.trade_code,
                        'trade_amount': trade.trade_amount,
                        'reduce_amount': trade.reduce_amount,
                        'state': trade.state,
                        'bill_code': trade.bill_id.code,
                        'operate_type': trade.bill_log_id.operate_type,
                        'start_bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date)),
                        'bill_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date)),
                        'repayment_date': fields.Datetime.to_string(fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date)),
                    } for trade in payment_order.trade_list
                ]
            }
            request.env['ifs.message'].sudo().trigger_push(
                api_app, 'pay', message_body)

        return {
            'payment_info': {
                'payment_code': payment_order.seq_code,
                'merchant_code': payment_order.merchant_code,
                'pay_amount': payment_order.pay_amount,
                'state': payment_order.state,
                'approved_quota': payment_order.bill_id.sub_loan_account_id.approved_quota,
                'available_quota': payment_order.bill_id.sub_loan_account_id.available_quota,
            },
            'trade_list': [
                {
                    'trade_code': trade.trade_code,
                    'trade_amount': trade.trade_amount - trade.reduce_amount,
                    'state': trade.state,
                    'bill_code': trade.bill_id.code,
                    'operate_type': trade.bill_log_id.operate_type,
                    'start_bill_date': fields.Datetime.context_timestamp(trade, trade.bill_id.start_bill_date),
                    'bill_date': fields.Datetime.context_timestamp(trade, trade.bill_id.bill_date),
                    'repayment_date': fields.Datetime.context_timestamp(trade, trade.bill_id.repayment_date),
                } for trade in payment_order.trade_list
            ]
        }

    def chack_data(self, datas, fields):
        if datas:
            missing_fields = [field for field in fields if field not in datas or datas.get(
                field) is None or datas.get(field) == '']
            if len(missing_fields) > 0:
                raise UserError(f'以下必填字段不能为空: {", ".join(missing_fields)}')
        else:
            raise UserError(_('参数不能为空！'))
        
    def geth5faceid(self,userId,name,idNo,redirectUrl):
        app_id, secret, version = self.get_IdSecret()
        nonce = ''.join(random.sample(
                string.ascii_letters + string.digits, 32)).lower()
        ticket = self.get_sign_ticket()
        orderNo = 'YZSB' + ''.join(random.sample(
                string.ascii_letters + string.digits, 28)).lower()
        sign = self.generate_sign([app_id,orderNo,name,idNo,userId,version,ticket])
        resp = requests.post(f'https://kyc1.qcloud.com/api/server/h5/geth5faceid?orderNo={orderNo}',json={
            'appId':app_id,
            'orderNo':orderNo,
            'name':name,
            'idNo':idNo,
            'userId':userId,
            'version':version,
            'sign':sign,
            'ticket':ticket
        })
        resp_json = resp.json()
        if resp.status_code != 200 or resp_json.get('code') != '0':
            return UserError('上传身份信息错误')
        result = resp_json.get('result')
        optimalDomain = result.get('optimalDomain')
        h5faceId = result.get('h5faceId')
        sign1 = self.generate_sign([app_id,userId,orderNo,version,h5faceId,ticket,nonce])
        params = {
            'appId':app_id,
            'version':version,
            'nonce':nonce,
            'orderNo':orderNo,
            'h5faceId':h5faceId,
            'url':redirectUrl,
            'userId':userId,
            'sign':sign1,
            'resultType':'1'
        }
        encoded_params = urlencode(params)
        return f'https://{optimalDomain}/api/web/login?{encoded_params}'
        
    # 移动端人脸核身 查询结果
    def queryfacerecord(self,orderNo):
        app_id, secret, version = self.get_IdSecret()
        ticket = self.get_sign_ticket()
        nonce = ''.join(random.sample(
                string.ascii_letters + string.digits, 32)).lower()
        sign = self.generate_sign([app_id,orderNo,version,ticket,nonce])
        resp = requests.post(f'https://kyc1.qcloud.com/api/v2/base/queryfacerecord?orderNo={orderNo}',
                      json={
                          'appId':app_id,
                          'version':version,
                          'nonce':nonce,
                          'orderNo':orderNo,
                          'sign':sign,
                          'getFile':'1'
                      })
        return resp
        
    
    
    # 移动端上传身份信息 ，启动H5人脸核身
    def upload_identity_info(self,userId,name,idNo,url):
        app_id, secret, version = self.get_IdSecret()
        nonce = ''.join(random.sample(
                string.ascii_letters + string.digits, 32)).lower()
        ticket = self.get_sign_ticket()
        sign_list = [version, app_id,ticket,nonce, userId]
        sign = self.generate_sign(sign_list)
        print(sign)
        orderNo = 'YZSB' + ''.join(random.sample(
                string.ascii_letters + string.digits, 28)).lower()
        resp = requests.post(f'https://kyc1.qcloud.com/api/server/getAdvFaceId?orderNo={orderNo}',json={
            'appId':app_id,
            'orderNo':orderNo,
            'name':name,
            'idNo':idNo,
            'userId':userId,
            'version':version,
            'sign':sign,
            'nonce':nonce
        },headers={
            'Content-Type':'application/json'
        })
        _logger.info("人脸识别 上传身份信息返回:{}".format(resp.text))
        resp_json = resp.json()
        if resp_json.get('code') != '0':
            return UserError('上传身份信息错误')
        result = resp_json.get('result')
        optimalDomain = result.get('optimalDomain')
        sign1 = self.generate_sign([app_id,orderNo,userId,version,result.get('faceId'),ticket,nonce])
        
        params = {
            'appId':app_id,
            'version':version,
            'nonce':nonce,
            'orderNo':orderNo,
            'faceId':result.get('faceId'),
            'url':url,
            'userId':userId,
            'sign':sign1,
            'from':'browser',
            'resultType':'1'
        }
        encoded_params = urlencode(params)
        full_url = f'https://{optimalDomain}/api/web/login?{encoded_params}'
        print(full_url)
        return full_url
        
    def generate_sign(self,list_str):
        _logger.info("人脸识别 签名前数据:{}".format(list_str))
        list_str = sorted(list_str)
        sign_str = ''.join(list_str)
        sha1_hash = hashlib.sha1()
        sha1_hash.update(sign_str.encode('utf-8'))
        sign = sha1_hash.hexdigest().upper()
        return sign
        
    def get_access_token(self):
        app_id, secret, version = self.get_IdSecret()
        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            access_token = db.get(
                f"Weixin_AccessToken_{app_id}_{secret}"
            )
            if access_token:
                return access_token.decode()
        resp = requests.get('https://kyc1.qcloud.com/api/oauth2/access_token',params={
            'app_id':app_id,
            'secret':secret,
            'grant_type':'client_credential',
            'version':version
        })
        _logger.info("人脸识别 获取AccessToken返回:{}".format(resp.text))
        if resp.status_code == 200 and resp.json().get('success'):
            access_token = resp.json().get('access_token')
            with cache_base.redis_db.connection_open() as db:
                db.setex(
                    name = f"Weixin_AccessToken_{app_id}_{secret}",
                    value = access_token,
                    time = resp.json().get('expire_in')
                )
            return access_token
        raise UserError('获取 Access Token 错误')
    
    
    def get_sign_ticket(self):
        app_id, secret, version = self.get_IdSecret()
        access_token = self.get_access_token()
        cache_base = retrieve_cache_base(request.env, "TOKEN-CACHE")
        with cache_base.redis_db.connection_open() as db:
            sign_ticket = db.get(
                f"Weixin_SIGN_ticket_{app_id}"
            )
            if sign_ticket:
                return sign_ticket.decode()
        
        resp = requests.get('https://kyc1.qcloud.com/api/oauth2/api_ticket',params={
            'app_id':app_id,
            'access_token':access_token,
            'type':'SIGN',
            'version':version
        })
        resp_json = resp.json()
        _logger.info("人脸识别 获取ticket返回:{}".format(resp.text))
        if resp.status_code == 200 and resp_json.get('success') and len(resp_json.get('tickets')) > 0:
            ticket = resp_json.get('tickets')[0]
            with cache_base.redis_db.connection_open() as db:
                db.setex(
                    f"Weixin_SIGN_ticket_{app_id}",
                    value = ticket.get('value'),
                    time = ticket.get('expire_in')
                )
            return ticket.get('value')
        raise UserError('获取 SIGN ticket 错误')
    
    def get_IdSecret(self):
        # app_id = 'TIDAAwKU'
        # secret = 'FGzasBrKR4lUQJQ5f4tZqezyqxoYYGR4qCgqOejgEsmeS6lRKQl1D6o26pdPsODw'
        
        cfg = request.env['ir.config_parameter'].sudo()
        app_id = cfg.get_param('ifs.contract.face.app.id', False)
        secret = cfg.get_param('ifs.contract.face.app.secret', False)
        
        return app_id, secret, '1.0.0'
