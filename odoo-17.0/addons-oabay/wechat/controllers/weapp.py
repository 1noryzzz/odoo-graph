# -*- coding: utf-8 -*-

import json
import logging

from odoo import exceptions, http
from odoo.http import request
from wechatpy.exceptions import WeChatClientException

from ..rpc import weapp_entry
from .base import WechatBase

_logger = logging.getLogger(__name__)


class WechatWeapp(WechatBase):
    # @http.route()
    # def wechat_base_test(self, **kwargs):
    #     '''
    #     weapp_config = request.env['wechat.weapp.config'].search(
    #         [('website_id.id', '=?', 2)], limit=1)
    #     session_wizard = request.env['wechat.weapp.session.wizard'].search(
    #         [('open_id', '=', 'oGB495MA0filc_x9NgchLvzIU73s')], limit=1)
    #     request.env['wechat.weapp.user'].sudo().signup(
    #                     weapp_config, session_wizard)
    #     return 'ok'
    #     '''
    #     return 'ok1'

    def _retrieve_weapp_userinfo(self, open_id):
        session_wizard = request.env['wechat.weapp.session.wizard'].search(
            [('open_id', '=', open_id)], limit=1)
        weapp_user = request.env['wechat.weapp.user'].search(
            [('open_id', '=', open_id)], limit=1)

        if session_wizard.exists() and session_wizard.user_info:
            user_info = json.loads(session_wizard.user_info)
            user_info.pop('watermark')
            user_info.update({
                'is_registed': bool(weapp_user.exists())
            })
            return self.res_ok(user_info)
        elif weapp_user.exists():
            return self.res_ok(weapp_user.read_to_weapp())
        else:
            return self.res_err(10000)

    def _weapp_login(self, open_id, session_key, weapp_id):
        login_data = {
            'login_type': 'wechat_weapp',
            'open_id': open_id,
            'session_key': session_key,
            'weapp_id': weapp_id
        }
        request.env['wechat.weapp.session.wizard'].sudo(
        ).update_when_login(login_data)
        try:
            uid = request.session.authenticate(
                request.session.db, login_data, None)
            if not uid:
                return self.res_err(10000)
        except exceptions.ValidationError:
            return self.res_err(300)
        except exceptions.AccessDenied:
            if open_id:
                return self._retrieve_weapp_userinfo(open_id)
            return self.res_err(10000)

        return self._retrieve_weapp_userinfo(open_id)

    @http.route('/wechat/weapp_login', type='json', auth='public', website=True)
    def weapp_login(self, code, **kwargs):
        weapp_config = request.env['wechat.weapp.config'].search(
            [('website_id.id', '=?', request.website.id)], limit=1)
        if weapp_config.exists():
            entry = weapp_entry.retrieve_entry(
                request.env, weapp_config.app_id)

            try:
                session_info = entry.client.wxa.code_to_session(code)
            except WeChatClientException:
                return self.res_err(602)

            if session_info.get('errcode'):
                return session_info.get('errmsg')

            request.session['open_id'] = session_info['openid']
            return self._weapp_login(session_info['openid'],
                                     session_info['session_key'],
                                     weapp_config.id)
        else:
            return self.res_err(701)

    @http.route('/wechat/weapp_userinfo', type='json', auth='public', website=True)
    def weapp_userinfo(self, **kwargs):
        open_id = request.session.get('open_id', False)
        if open_id:
            return self._retrieve_weapp_userinfo(open_id)

        return self.res_err(902)

    @http.route('/wechat/weapp_bindinfo', type='json', auth='public', website=True)
    def weapp_bindinfo(self, iv, encryptedData, **kwargs):
        open_id = request.session.get('open_id', False)
        if open_id:
            weapp_config = request.env['wechat.weapp.config'].search(
                [('website_id.id', '=?', request.website.id)], limit=1)
            if weapp_config.exists():
                request.env['wechat.weapp.session.wizard'].sudo().cache_user_info(
                    open_id, weapp_config.id, weapp_config.app_id, iv, encryptedData)

                return self.res_ok()
            else:
                return self.res_err(701)

        return self.res_err(902)

    @http.route('/wechat/weapp_bindphone', type='json', auth='public', website=True)
    def weapp_bindphone(self, iv, encryptedData, **kwargs):
        open_id = request.session.get('open_id', False)
        if open_id:
            weapp_config = request.env['wechat.weapp.config'].search(
                [('website_id.id', '=?', request.website.id)], limit=1)
            if weapp_config.exists():
                session_wizard = request.env['wechat.weapp.session.wizard'].sudo().cache_phone_info(
                    open_id, weapp_config.id, weapp_config.app_id, iv, encryptedData)

                if session_wizard.exists():
                    request.env['wechat.weapp.user'].sudo().signup(
                        weapp_config, session_wizard)

                    return self.res_ok()
            else:
                return self.res_err(701)

        return self.res_err(902)
