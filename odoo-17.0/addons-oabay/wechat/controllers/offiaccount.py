# -*- coding: utf-8 -*-

import json
import base64
import logging
import random
import string
import time
from urllib.parse import quote, unquote

import werkzeug
from odoo import _, http, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import AccessDenied, ValidationError
from wechatpy import create_reply, parse_message
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
from wechatpy.oauth import WeChatOAuth
from wechatpy.utils import check_signature

from werkzeug.urls import url_encode, url_quote_plus, url_unquote_plus

from .base import WechatBase

_logger = logging.getLogger(__name__)


class WechatOffiaccount(WechatBase):

    def get_qr_providers(self, *args, **kw):
        qr_providers = super().get_qr_providers(*args, **kw)

        offiaccount = request.env['wechat.offiaccount.config'].sudo().search(
            ['&', ('website_id', '=', request.website.id), ('is_default', '=', True)], limit=1)
        if offiaccount.exists() and offiaccount.qr_login_id and offiaccount.qr_login_id.enabled:
            qr_login = offiaccount.qr_login_id
            # redirect = kw.get('redirect', None)
            # if redirect and not (redirect.lower().startswith('http://') or redirect.lower().startswith('https://')):
            #     redirect = '%s%s' % (request.website.domain, redirect)

            qr_providers.append({
                'action_name': 'wechat_offiaccount',
                'appid': qr_login.app_id,
                'redirect_uri': quote('%s/wechat/offiaccount_auth' % request.website.domain),
                'scope': qr_login.scope,
                'css_class': qr_login.css_class,
                'body': qr_login.body,
                'sequence': qr_login.sequence,
                'state': base64.b64encode(json.dumps({
                    'appid': qr_login.app_id,
                    'redirect': kw.get('redirect', qr_login.redirect_uri),
                }).encode('utf-8')).decode('utf-8'),
            })

        return qr_providers

    @http.route('/wechat/<app_id>/handle_message', type='http', auth="public", methods=['GET', 'POST'], sitemap=False, csrf=False)
    def handle_message(self, app_id, **kwargs):
        offiaccount, entry = request.env['wechat.offiaccount.config'].sudo(
        ).retrieve_entry(app_id=app_id)
        request.entry = entry

        msg_signature = kwargs.get('msg_signature', '')
        signature = kwargs.get('signature', '')
        timestamp = kwargs.get('timestamp', '')
        nonce = kwargs.get('nonce', '')
        encrypt_type = kwargs.get('encrypt_type', 'raw')

        try:
            check_signature(
                entry.message_token,
                signature,
                timestamp,
                nonce
            )
        except InvalidSignatureException:
            return self._abort(403)

        if request.httprequest.method == 'GET':
            return kwargs.get('echostr', '')

        msg = None
        if encrypt_type == 'raw':
            # plaintext mode
            msg = parse_message(request.httprequest.data)
        else:
            # encryption mode
            try:
                msg = entry.crypto_handle.decrypt_message(
                    request.httprequest.data,
                    msg_signature,
                    timestamp,
                    nonce
                )
            except (InvalidSignatureException, InvalidAppIdException):
                return self._abort(403)
            msg = parse_message(msg)

        _logger.info("Receive message %s" % msg)

        cb_action_conditions = [
            ('value_from', '=', 'wechat'), ('active', '=', True)]
        value_code = msg.type
        if value_code == 'event':
            value_code = msg.event
            cb_action_conditions.append(
                ('value_code_ids.value_type', '=', msg.type))

        cb_action_conditions.append(('value_code_ids.value', '=', value_code))
        cb_actions = request.env['oa.callback.action'].sudo().search(
            cb_action_conditions)

        replys = []
        for cb_action in cb_actions:
            request.uid = cb_action.user_id.id
            cb_log = request.env['oa.callback.log'].info(
                offiaccount.website_id.company_id.id, value_code,
                cb_action, msg, source=msg.source, target=msg.target)

            ret = cb_action.process(entry, msg, cb_log)
            if ret:
                replys.append(ret)

        raw_reply = ';'.join(replys)
        if raw_reply:
            reply = create_reply(raw_reply, message=msg, render=True)
            if encrypt_type == 'raw':
                return reply
            else:
                _logger.info("Reply message %s" % reply)
                res = entry.crypto_handle.encrypt_message(
                    reply, nonce, timestamp)
                return res
        else:
            return ''

    @http.route('/wechat/offiaccount_rd', type='http', auth="public", website=True, sitemap=False)
    def offiaccount_redirect(self, redirect=None, binding=False, **kw):
        if redirect:
            offiaccount = request.env['wechat.offiaccount.config'].sudo().search(
                ['&', ('website_id', '=', request.website.id), ('is_default', '=', True)], limit=1)
            if offiaccount.exists():
                oauth = WeChatOAuth(
                    offiaccount.app_id, offiaccount.secret,
                    '%s/wechat/%s' % (request.website.domain,
                                      'offiaccount_binding' if binding else 'offiaccount_auth'),
                    scope='snsapi_userinfo' if binding else 'snsapi_base',
                    state=base64.b64encode(json.dumps({
                        'redirect': redirect,
                    }).encode('utf-8')).decode('utf-8'))
                return werkzeug.utils.redirect(oauth.authorize_url)

        return self._abort(403)

    @http.route('/wechat/offiaccount_binding', type='http', auth="user", website=True, sitemap=False)
    def offiaccount_binding(self, **kw):
        code = kw.get('code')
        state = json.loads(base64.b64decode(
            kw.get('state').encode('utf-8')).decode('utf-8'))
        redirect = state.get('redirect')
        appid = state.get('appid')
        if code:
            offiaccount, entry = request.env['wechat.offiaccount.config'].sudo(
            ).retrieve_entry(app_id=appid)
            oauth = WeChatOAuth(
                offiaccount.app_id, offiaccount.secret,
                '%s/wechat/offiaccount_auth' % request.website.domain)
            access_token = oauth.fetch_access_token(code)
            if access_token.get('errcode'):
                return access_token.get('errmsg')
            else:
                user_info = oauth.get_user_info(openid=access_token.get(
                    'openid'), access_token=access_token.get('access_token'))
                request.env['wechat.offiaccount.user'].sudo().signup(
                    offiaccount, user_info, user_id=request.uid)
                return werkzeug.utils.redirect(redirect)

    @http.route('/wechat/offiaccount_auth', type='http', auth="public", website=True, sitemap=False)
    def offiaccount_auth(self, **kw):
        code = kw.get('code')
        state = json.loads(base64.b64decode(
            kw.get('state').encode('utf-8')).decode('utf-8'))
        redirect = state.get('redirect')
        appid = state.get('appid')
        if code:
            offiaccount = request.env['wechat.offiaccount.config'].sudo().search(
                ['&', ('website_id', '=', request.website.id), ('is_default', '=', True)], limit=1)

            if appid and offiaccount.qr_login_id and offiaccount.qr_login_id.app_id == appid:
                oauth = WeChatOAuth(
                    offiaccount.qr_login_id.app_id, offiaccount.qr_login_id.secret,
                    '%s/wechat/offiaccount_auth' % request.website.domain)
            else:
                oauth = WeChatOAuth(
                    offiaccount.app_id, offiaccount.secret,
                    '%s/wechat/offiaccount_auth' % request.website.domain)
            access_token = oauth.fetch_access_token(code)
            if access_token.get('errcode'):
                return access_token.get('errmsg')
            else:
                old_uid = request.uid
                try:
                    login_data = {
                        'login_type': 'wechat_offiaccount',
                        'union_id': access_token.get('unionid'),
                        'open_id': access_token.get('openid'),
                        'offiaccount_id': offiaccount.id
                    }

                    if not request.uid:
                        request.uid = SUPERUSER_ID

                    uid = request.session.authenticate(
                        request.session.db, login_data, None)
                    if uid:
                        request.params['login_success'] = True
                        return werkzeug.utils.redirect(redirect)
                except ValidationError:
                    pass
                except AccessDenied:
                    pass

                request.uid = old_uid
                return werkzeug.utils.redirect('/web/login')

        return self._abort(403)

    @http.route('/wechat/offiaccount_sharing', type='http', auth="public", website=True, sitemap=False)
    def offiaccount_sharing(self, **kw):
        nonce_str = ''.join(random.sample(
            string.ascii_letters + string.digits, 10))
        offiaccount = request.env['wechat.offiaccount.config'].sudo().search(
                ['&', ('website_id', '=', request.website.id), ('is_default', '=', True)], limit=1)
        if not offiaccount.app_id:
            raise ValidationError(_('微信公众号配置错误！'))

        offiaccount, entry = request.env[
            'wechat.offiaccount.config'].retrieve_entry(
            app_id=offiaccount.app_id)
        jsapi_ticket = entry.client.jsapi.get_jsapi_ticket()
        timestamp = int(time.time())
        url = f"{request.website.domain.lower().replace('http://', 'https://')}/wechat/offiaccount_sharing"

        return request.render("wechat.wechat_offiaccount_sharing", {
            'wx_config': {
                'app_id': offiaccount.app_id,
                'timestamp': timestamp,
                'nonceStr': nonce_str,
                'signature': entry.client.jsapi.get_jsapi_signature(nonce_str, jsapi_ticket, timestamp, url),
                'url': url,
                'domain': request.website.domain,
            }
        })