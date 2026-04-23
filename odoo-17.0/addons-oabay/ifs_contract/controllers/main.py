# -*- coding: utf-8 -*-

import base64
import fitz
import io
import json
import werkzeug
import PyPDF2
import random
import string
import time
import qrcode
import requests
import hashlib

from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import reduce
from urllib.parse import urlencode, quote, unquote

from odoo import _, http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from cache_base import retrieve_cache_base

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.faceid.v20180301 import faceid_client, models

from PyPDF2 import PdfFileReader
from PIL import Image


class InclusiveFinancingContract(http.Controller):
    _WECHAT_AGENT = ['MicroMessenger', 'WeChat', 'wechatdevtools']
    _MOBILE_AGENT = ['Android', 'iPhone', 'iPad', 'iPod', 'Windows Phone', 'MQQBrowser']

    @http.route('/contract/sign/image/<int:id>/<string:field>', type='http', methods=['GET'], auth="public")
    def contract_sign_image(self, id, field, **kwargs):
        model = 'ifs.contract.info'

        return request.env['ir.http'].sudo()._content_image(
            model=model, res_id=id, field=field, quality=int(kwargs.get('quality', 0)))

    @http.route('/contract/sign', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_sign_page(self, token, **kwargs):
        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(
            token, check_validity=True)
        if sign_token:
            nonce_str = ''.join(random.sample(
                string.ascii_letters + string.digits, 10))
            offiaccount = request.env['wechat.offiaccount.config'].sudo().search(
                    ['&', ('website_id', '=', request.website.id), ('is_default', '=', True)], limit=1)
            # if not offiaccount.app_id:
            #     return request.render(
            #         'ifs_contract.contract_alert_msg', {
            #             'alert_msg': _('微信公众号配置错误！')
            #     })

            render_values = {
                'contract_infos': sign_token.contract_info_ids,
                'sign_token': sign_token,
            }

            if offiaccount.app_id:
                offiaccount, entry = request.env[
                    'wechat.offiaccount.config'].retrieve_entry(app_id=offiaccount.app_id)
                jsapi_ticket = entry.client.jsapi.get_jsapi_ticket()
                timestamp = int(time.time())
                url = f"{request.website.domain.lower().replace('http://', 'https://')}/contract/sign?token={sign_token.token}"
                render_values.update({
                    'wx_config': {
                        'app_id': offiaccount.app_id,
                        'timestamp': timestamp,
                        'nonceStr': nonce_str,
                        'signature': entry.client.jsapi.get_jsapi_signature(nonce_str, jsapi_ticket, timestamp, url),
                        'url': url,
                        'domain': request.website.domain,
                    }
                })
            return request.render(
                'ifs_contract.contract_sign_before', render_values)
        else:
            return request.render(
                'ifs_contract.contract_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    def _prepare_client(self):
        cfg = request.env['ir.config_parameter'].sudo()
        face_secret_id = cfg.get_param('ifs.contract.face.secret.id', False)
        face_secret_key = cfg.get_param('ifs.contract.face.secret.key', False)
        cred = credential.Credential(
            face_secret_id, face_secret_key)

        # cred = credential.Credential(
        #     "AKIDFLDvPfgT2MSJwKURAfvwiFWYKtCG4dwz", "sVsJiy3zqbHrMl4HNWbWL7kS5VvCRXQ7")
        httpProfile = HttpProfile()
        httpProfile.endpoint = "faceid.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = faceid_client.FaceidClient(cred, "", clientProfile)

        return client

    @http.route('/contract/faceid', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def contract_faceid(self, token, **kw):
        user_agent = request.httprequest.headers.get('User-Agent')
        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(
            token, check_validity=True)
        if sign_token and sign_token.need_faceid:
            if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
                client = self._prepare_client()
                req = models.DetectAuthRequest()
                params = {
                    "IdCard": sign_token.sign_idcard,
                    "Name": sign_token.sign_name,
                    "RedirectUrl": "%s/contract/do_signature?token=%s" % (request.website.domain, token),
                    "RuleId": "1",
                }
                req.from_json_string(json.dumps(params))
                resp = client.DetectAuth(req)

                return werkzeug.utils.redirect(resp.Url)
            elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
                # TODO: 移动端人脸核身
                RedirectUrl = "%s/contract/do_signature?token=%s" % (request.website.domain, token)
                try:
                    full_url = self.upload_identity_info(f'userId_{sign_token.sign_idcard}',sign_token.sign_name,sign_token.sign_idcard,RedirectUrl)
                    return werkzeug.utils.redirect(full_url)
                except UserError as e:
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token, 
                            'alert_msg': e.args[0]
                        })
                
            else:
                # TODO: PC端人脸核身
                RedirectUrl = "%s/contract/do_signature?token=%s" % (request.website.domain, token)
                try:
                    full_url = self.geth5faceid(f'userId_{sign_token.sign_idcard}',sign_token.sign_name,sign_token.sign_idcard,RedirectUrl)
                    return werkzeug.utils.redirect(full_url)
                except UserError as e:
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token, 
                            'alert_msg': e.args[0]
                        })
        else:
            return request.redirect('/contract/do_signature?token=%s' % token)
        
    @http.route('/contract/test_error', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def test_error_signature(self, token, **kw):
        return request.render(
            'ifs_contract.match_face_error_msg_page', {
                'sign_token': token, 
                'alert_msg': '11111'
            })

    @http.route('/contract/do_signature', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def contract_do_signature(self, token, **kw):
        user_agent = request.httprequest.headers.get('User-Agent')
        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(
            token, check_validity=True)
        if sign_token and sign_token.need_faceid:
            if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
                client = self._prepare_client()
                req = models.GetDetectInfoEnhancedRequest()
                params = {
                    "BizToken": kw.get('BizToken', ''),
                    "RuleId": "1"
                }
                req.from_json_string(json.dumps(params))
                resp = client.GetDetectInfoEnhanced(req)
                if resp.Text.ErrCode == 0:
                    sign_token.write({
                        'liveness_video': resp.VideoData.LivenessVideo,
                        'best_frame': resp.BestFrame.BestFrame
                    })
                    return request.render(
                        'ifs_contract.contract_sign_template', {
                            'sign_token': sign_token
                        })
                else:
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token, 
                            'alert_msg': resp.Text.ErrMsg
                        })
            elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
                # 查询核身结果
                orderNo = kw.get('orderNo')
                resp = self.queryfacerecord(orderNo)
                if resp.status_code != 200:
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token,
                            'alert_msg': '获取认证结果失败'
                        })
                resp_data = resp.json()
                if resp_data.get('code') != '0':
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token,
                            'alert_msg': resp_data.get('msg')
                        })
                result = resp_data.get('result')
                sign_token.write({
                        'liveness_video': result.get('video'),
                        'best_frame': result.get('photo'),
                    })
                return request.render(
                        'ifs_contract.contract_sign_template', {
                            'sign_token': sign_token
                        })
            else:
                # 查询核身结果
                orderNo = kw.get('orderNo')
                resp = self.queryfacerecord(orderNo)
                if resp.status_code != 200:
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token,
                            'alert_msg': '获取认证结果失败'
                        })
                resp_data = resp.json()
                if resp_data.get('code') != '0':
                    return request.render(
                        'ifs_contract.match_face_error_msg_page', {
                            'sign_token': token,
                            'alert_msg': resp_data.get('msg')
                        })
                result = resp_data.get('result')
                sign_token.write({
                        'liveness_video': result.get('video'),
                        'best_frame': result.get('photo'),
                    })
                return request.render(
                        'ifs_contract.contract_sign_template', {
                            'sign_token': sign_token
                        })
        elif sign_token:
            return request.render(
                'ifs_contract.contract_sign_template', {
                    'sign_token': sign_token
                })
        else:
            return request.render(
                'ifs_contract.contract_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })

    @http.route('/contract', type='http', methods=['GET'], auth="public", website=True, csrf=False)
    def get_contract(self, **kw):
        contract_info = request.env['ifs.contract.info'].sudo().search(
            [('id', '=', kw.get('contract_id'))])
        contract_template_code = contract_info.template_id.code
        if contract_template_code == 'F41':
            page_title = '授权书详情'
        elif contract_template_code == 'F42' or contract_template_code == 'F43':
            page_title = '协议详情'
        else:
            page_title = '' 

        # return '<html><head><title>%s</title>\
        #         <meta content="width=device-width, initial-scale=1,maximum-scale=1,maximum-scale=1, user-scalable=no" name="viewport"/>\
        #         </head>%s<div class="return_last_page"><img class="tips-icon" src="/ifs_contract/static/img/return.png"/>\
        #         <a href="/contract/sign?token=%s">返回上一页</a></div></html>' % (
        #     page_title, contract_info.report_content, contract_info.token_ids.token)
        return request.render(
            'ifs_contract.contract_details_check', {
                'page_title': page_title,
                'sign_token': contract_info.token_ids.token,
                'report_content': contract_info.report_content
            })

    @http.route('/contract/signature', type='json', auth="public", website=True)
    def contract_signature(self, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        token = access_token or request.httprequest.args.get(
            'token')
        if not signature:
            return {'error': _('未收到签名信息')}

        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(
            token, check_validity=True)
        if sign_token:
            request.update_env(user=sign_token.user_id.id, context={
                **request.env.context,
                'allowed_company_ids': sign_token.user_id.company_ids.ids
            })
            sign_token = request.env['ifs.contract.info.sign.token'].sudo(
            ).sign_with_token(token, check_validity=True)
                
            # 判断所签署的合同中是否包含征信授权书
            is_credit = 'false'
            if sign_token.sign_partner._name == 'ifs.gar.entry.merchant' and sign_token.sign_partner.f41_contract_state in ['draft', 'unconfirmed']:
                is_credit = 'true'

            im = Image.open(io.BytesIO(base64.b64decode(signature)))
            if im.width < im.height:
                im = im.rotate(90, expand=True)
                b = io.BytesIO()
                im.save(b, format="PNG")
                signature = base64.b64encode(b.getvalue())

            for contract_info in sign_token.contract_info_ids:
                param = {
                    '_'.join([
                        sign_token.token_type,
                        'signature'
                    ]): signature,
                    'state': sign_token.next_state,
                    '_'.join([
                        sign_token.token_type,
                        'liveness_video'
                    ]): sign_token.liveness_video,
                    '_'.join([
                        sign_token.token_type,
                        'best_frame'
                    ]): sign_token.best_frame,
                }
                if sign_token.is_sync:
                    param['state'] = 'confirmed'
                contract_info.write(param)

            interactive_url = False
            if sign_token.next_state == 'signed':
                if sign_token.is_sync:
                    sign_token.write({
                        'sync_state': 'user_sign'
                    })
                    cron = request.env['ir.cron'].sudo().env.ref(
                        'ifs_contract.commit_user_sign_cron')
                    request.env['ir.cron.trigger'].sudo().create(
                        {'cron_id': cron.id, 'call_at': datetime.now() +
                         relativedelta(seconds=5)}
                    )
                elif sign_token.need_sms_verify:
                    interactive_url = sign_token.contract_info_ids.with_context(
                        uid=sign_token.user_id.id).signature_all_by_interactive('OABAY_P', sign_token.sign_partner)
                else:
                    sign_token.contract_info_ids.with_context(
                        uid=sign_token.user_id.id).signature_all()

            act = None
            if sign_token.ref_object:
                act = sign_token.ref_object.after_sign(sign_token.next_state)

            target = sign_token.user_id.partner_id
            request.env['bus.bus']._sendone(target, 'ifs_contract_signed', act)
            request.env['bus.bus']._sendone(target, 'ifs_contract_parent_close', act)

            additional_info = ''
            if act and act.get('type') == 'ir.actions.client' and act.get('tag') == 'display_notification' and act.get('params').get('next_url'):
                additional_info = f"&next_url={quote(act.get('params').get('next_url'))}&next_name={quote(act.get('params').get('next_name'))}&next_description={quote(act.get('params').get('next_description'))}"

            if interactive_url:
                return {
                    'force_refresh': True,
                    'redirect_url': interactive_url
                }

            return {
                'force_refresh': True,
                'redirect_url': '/contract/sign_finish?token=' + token + '&credit=' + is_credit + additional_info
            }
        else:
            return {'error': _('TOKEN 无效')}

    @http.route('/contract/sign_finish', type='http', methods=['GET'], auth="public", website=True)
    def contract_signed(self, token, **kw):
        credit = kw.get('credit', 'false')
        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(token, check_validity=True)
        if not sign_token:
            return request.render(
                'ifs_contract.contract_alert_msg', {
                    'alert_msg': _('TOKEN 无效')
                })
        entry_merchant = sign_token.sign_partner
        if not entry_merchant:
            return request.render(
                'ifs_contract.contract_alert_msg', {
                    'alert_msg': _('TOKEN未关联有效的进件记录！')
                })
        api_app = request.env['galaxy.open.api.app'].sudo().search(
            [('owner_id', '=', f'ifs.partner.supplier,{entry_merchant.supplier_id.id}')], limit=1)
        
        if api_app and api_app.id:
            if credit == 'true':
                authorization_callback_url = api_app.authorization_callback_url
                first_url_join_symbol = '&' if '?' in authorization_callback_url else '?'
                callback_url = f'{authorization_callback_url}{first_url_join_symbol}entry_code={entry_merchant.seq_code}&state={entry_merchant.state}'
            else:
                contract_callback_url = api_app.contract_callback_url
                first_url_join_symbol = '&' if '?' in contract_callback_url else '?'
                callback_url = f'{contract_callback_url}{first_url_join_symbol}entry_code={entry_merchant.seq_code}&state={entry_merchant.state}'
        else:
            callback_url = ''
        
        if not sign_token.is_sync:
            sign_token.unlink()
                
        return request.render('ifs_contract.contract_signed', {
            'contract_callback_url': callback_url,
            'next_url': unquote(kw.get('next_url', '')),
            'next_name': unquote(kw.get('next_name', '')),
            'next_description': unquote(kw.get('next_description', ''))
        })

    # 刷新合同预览图
    @http.route('/contract/refresh_contract_preview', type='http', methods=['GET'], auth="user", website=True)
    def refresh_contract_preview(self, **kw):
        contracts = request.env['ifs.contract.info'].sudo().search(
            [('state', '=', 'signed')])
        # contracts = request.env['ifs.contract.info'].sudo().browse([356])
        for contract in contracts:
            try:
                if contract.contract and not contract.contract_preview:
                    desired_width = 300
                    desired_height = 190
                    with io.BytesIO(base64.b64decode(contract.contract)) as pdf_stream:
                        pdf_reader = PdfFileReader(pdf_stream)
                        if pdf_reader.numPages > 0:
                            first_page = pdf_reader.getPage(0)
                            # 计算截图的长宽
                            new_width = int(first_page.mediaBox[2])
                            new_height = int(
                                new_width / (desired_width / desired_height))
                            # 使用 PyMuPDF 将 PDF 页面转换为图像
                            doc = fitz.open(stream=pdf_stream, filetype="pdf")
                            pixmap = doc.load_page(0).get_pixmap()
                            pdf_image = Image.frombytes(
                                "RGB", (pixmap.width, pixmap.height), pixmap.samples)
                            # 调整图像大小并进行截图
                            pdf_image = pdf_image.crop(
                                (0, 0, new_width, new_height))
                            pdf_image = pdf_image.resize(
                                (desired_width * 2, desired_height * 2), Image.ANTIALIAS)
                            # 将图像保存为字节流
                            image_stream = io.BytesIO()
                            pdf_image.save(image_stream, format='JPEG')
                            image_stream.seek(0)
                            # 将字节流编码为 base64 字符串
                            encoded_image = base64.b64encode(
                                image_stream.read())
                            # 设置截图字段的值为编码后的图像数据
                            contract.contract_preview = encoded_image.decode()
                        # 关闭 PDF 文件
                        doc.close()
            except PyPDF2.utils.PdfReadError:
                continue

        return _('合同预览刷新成功！')
    
    @http.route(['/contract/generate/share_qrcode'], type='json', auth="public", cors="*", methods=['POST'], website=True)
    def generate_share_qrcode(self, token):
        sign_token = request.env['ifs.contract.info.sign.token'].sudo().sign_with_token(
            token, check_validity=True)
        url = request.httprequest.host_url + \
            'contract/sign?token=' + sign_token.token
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
            'url': url,
            'qrCodeSrc': qr_image.decode()
        }
    
    @http.route('/mp/MP_verify_JZlxZyKYY6l0WWJ6.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_wapp_mp_mp(self, **kwargs):
        return 'JZlxZyKYY6l0WWJ6'
    
    @http.route('/MP_verify_JZlxZyKYY6l0WWJ6.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_wapp_mp(self, **kwargs):
        return 'JZlxZyKYY6l0WWJ6'

    
    
    # PC端上传身份信息，启动H5人脸核身
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
            raise UserError('上传身份信息错误')
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
        resp_json = resp.json()
        if resp_json.get('code') != '0':
            raise UserError('上传身份信息错误')
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