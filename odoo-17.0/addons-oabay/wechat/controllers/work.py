# -*- coding: utf-8 -*-

import base64
import json
import logging
import random
import string
import time
from urllib.parse import quote, unquote

import requests
import werkzeug
from odoo import SUPERUSER_ID, http
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request
from wechatpy.exceptions import (InvalidSignatureException,
                                 WeChatClientException)
from wechatpy.work import create_reply, parse_message
from wechatpy.work.exceptions import InvalidCorpIdException

from .base import WechatBase

_logger = logging.getLogger(__name__)


def _do_rpc_login(comm_var, db, login, password):
    return json.loads(comm_var.get('rpc').post(''.join([
        comm_var.get('base_url'), 'web/session/authenticate']), json={
            'id': int(time.time()),
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'db': db,
                'login': login,
                'password': password,
            }
    }).text).get('result')


def _do_rpc(comm_var, call_kw, params):
    comm_var['base_url'] = 'https://www.sztxtr.com/'
    if comm_var.get('rpc') == None:
        comm_var['rpc'] = requests.Session()
        comm_var['rpc_context'] = _do_rpc_login(
            comm_var, 'txtr_db', '815523739@qq.com', 'aabbccdd11223344').get('user_context')

    return json.loads(comm_var.get('rpc').post(''.join([
        comm_var.get('base_url'), 'web/dataset/', call_kw]), json={
        'id': int(time.time()),
        'jsonrpc': '2.0',
        'method': 'call',
        'params': params,
    }).text).get('result')


def _retrieve_answer_token(union_id):
    comm_var = {}
    partner_info = _do_rpc(comm_var, 'search_read', {
        'model': 'res.partner',
        'fields': ['id', 'name'],
        'domain': [('unionid', '=', union_id)],
    })

    if partner_info.get('length') == 1:
        answer_token = _do_rpc(comm_var, 'search_read', {
            'model': 'physical.user_input',
            'fields': ['id', 'token'],
            'domain': ['&', ('state', '=', 'done'), ('partner_id', '=', partner_info.get('records')[0].get('id'))],
            'sort': 'write_date desc',
            'limit': 1
        })

        if answer_token.get('length') > 0:
            return answer_token.get('records')[0].get('token')
        else:
            return ''
    else:
        raise ValidationError(u'用户在旧系统中不存在！')


class WechatWework(WechatBase):

    def get_qr_providers(self, *args, **kw):
        qr_providers = super().get_qr_providers(*args, **kw)

        wechat_work = request.env['wechat.work.config'].sudo().search(
            [('company_id', '=', request.website.company_id.id)])
        agents = wechat_work.agent_ids.filtered(
            lambda agent: agent.qr_login_id and agent.qr_login_id.enabled
            and agent.qr_login_id.website_id.id == request.website.id)
        if agents.exists():
            agent = agents[0]
            qr_login = agent.qr_login_id
            qr_providers.append({
                'action_name': 'wechat_work',
                'appid': qr_login.app_id,
                'agentid': agent.agent_id,
                'redirect_uri': quote('%s/wechat/work_auth' % request.website.domain),
                'scope': qr_login.scope,
                'css_class': qr_login.css_class,
                'body': qr_login.body,
                'sequence': qr_login.sequence,
                'state': base64.b64encode(json.dumps({
                    'agent_id': agent.agent_id,
                    'redirect': kw.get('redirect', qr_login.redirect_uri),
                }).encode('utf-8')).decode('utf-8'),
            })
        return qr_providers

    @http.route('/wechat/work_test', type='http', auth="user", website=True, sitemap=False)
    def wechat_work_test(self, **kwargs):
        wechat_work, entry = request.env['wechat.work.config'].retrieve_entry(
            request.website.company_id.id)
        if entry.ext_contacts_client:
            external_userids = []
            has_ext_contact_users = entry.ext_contacts_client.external_contact.get_follow_user_list()
            if has_ext_contact_users.get('errcode') == 0:
                for user_id in has_ext_contact_users.get('follow_user'):
                    try:
                        ext_info = entry.ext_contacts_client.external_contact.list(
                            user_id)
                        if ext_info.get('errcode') == 0:
                            external_userids += ext_info.get('external_userid')
                    except WeChatClientException:
                        pass

            ext_user_details = []
            for ext_user_id in external_userids:
                ext_user_details.append(
                    entry.ext_contacts_client.external_contact.get(ext_user_id))

            return json.dumps(ext_user_details, ensure_ascii=False, indent=4)
        else:
            return 'no external contact client'

    @http.route(['/wechat/work', '/wechat/<agent_id>/work'], type='http', auth="none")
    def work(self, agent_id=None, s_action=None, **kw):
        if not request.session.uid:
            if agent_id:
                return werkzeug.utils.redirect(
                    '/wechat/work_rd?agent_id={}&redirect=/web'.format(agent_id), 303)
            else:
                return werkzeug.utils.redirect(
                    '/wechat/work_rd?redirect=/web', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)

        return werkzeug.utils.redirect('/web', 303)

    @http.route('/wechat/<agent_id>/handle_work_message', type='http', auth="public", website=True, sitemap=False, csrf=False)
    def handle_work_message(self, agent_id, **kwargs):
        _logger.warning(kwargs)
        wechat_work, entry = request.env['wechat.work.config'].sudo().retrieve_entry(
            request.website.company_id.id)
        request.entry = entry
        request.wechat_work = wechat_work
        try:
            if request.httprequest.method == 'GET':
                echo_str = entry.crypto_handle[agent_id].check_signature(
                    kwargs.get('msg_signature'), kwargs.get(
                        'timestamp'), kwargs.get('nonce'), kwargs.get('echostr')
                )
                return echo_str
            else:
                msg = parse_message(entry.crypto_handle[agent_id].decrypt_message(
                    request.httprequest.data,
                    kwargs.get('msg_signature'),
                    kwargs.get('timestamp'),
                    kwargs.get('nonce')
                ))
                _logger.warning(msg)
                ret = ''
                request.uid = request.env.ref(
                    'wechat.wechat_work_message_push_user_id').id
                if msg.type in ['text', 'image', 'voice', 'location']:
                    #reply = create_reply(msg.content, msg).render()
                    from .handlers.text_handler import work_autoreply_handler
                    ret = work_autoreply_handler(request, msg)
                elif msg.type == 'event':
                    if msg.event == 'subscribe':
                        from .handlers.work_event_handler import subscribe_handler
                        ret = subscribe_handler(request, msg)
                    elif msg.event == 'unsubscribe':
                        from .handlers.work_event_handler import unsubscribe_handler
                        ret = unsubscribe_handler(request, msg)
                    elif msg.event == 'change_contact':
                        from .handlers.work_event_handler import change_contact_handler
                        ret = change_contact_handler(request, msg)
                elif msg.type == 'unknown':
                    ret = self.handle_unknown(msg)

                return entry.crypto_handle[agent_id].encrypt_message(
                    create_reply(ret, msg, render=True),
                    kwargs.get('nonce'),
                    kwargs.get('timestamp'))
        except (InvalidSignatureException, InvalidCorpIdException):
            return ''

    @http.route('/wechat/work_rd', type='http', auth="public", website=True, sitemap=False)
    def wechat_redirect(self, agent_id=None, redirect=None, **kw):
        if redirect:
            wechat_work, entry = request.env['wechat.work.config'].sudo().retrieve_entry(
                request.website.company_id.id)
            if not agent_id:
                agent_id = wechat_work.default_agent_id
            if entry.app_id:
                return werkzeug.utils.redirect(entry.clients[agent_id].oauth.authorize_url(
                    '%s/wechat/work_auth' % request.website.domain, base64.b64encode(json.dumps({
                        'agent_id': agent_id,
                        'redirect': redirect,
                    }).encode('utf-8')).decode('utf-8')))

        return self._abort(403)

    @http.route('/wechat/work_auth', type='http', auth="public", website=True, sitemap=False)
    def wechat_auth(self, **kw):
        code = kw.get('code')
        state = json.loads(base64.b64decode(
            kw.get('state').encode('utf-8')).decode('utf-8'))
        agent_id = state.get('agent_id')
        redirect = state.get('redirect')
        if code:
            wechat_work, entry = request.env['wechat.work.config'].sudo().retrieve_entry(
                request.website.company_id.id)
            if entry.app_id:
                try:
                    user_info = entry.clients[agent_id].oauth.get_user_info(
                        code)
                except WeChatClientException:
                    return self._abort(403)

                if user_info.get('errcode'):
                    return user_info.get('errmsg')
                else:
                    old_uid = request.uid
                    try:
                        login_data = {
                            'login_type': 'wechat_work',
                            'open_id': user_info.get('UserId'),
                            'user_id': user_info.get('UserId'),
                            'work_id': wechat_work.id
                        }
                        uid = request.session.authenticate(
                            request.session.db, login_data, None)
                        if uid:
                            return werkzeug.utils.redirect(redirect)
                    except ValidationError:
                        pass
                    except AccessDenied:
                        pass

                    request.uid = old_uid
                    return werkzeug.utils.redirect('/web/login')

        return self._abort(403)

    @http.route(['/wechat/work/test', '/wechat/work/<aid>/test'], type='http', auth="public", website=True, sitemap=False)
    def wechat_work_user_get(self, aid=False, **kwargs):
        wechat_work, entry = request.env['wechat.work.config'].retrieve_entry(
            request.website.company_id.id)

        nonce_str = ''.join(random.sample(
            string.ascii_letters + string.digits, 10))
        jsapi_ticket = entry.contacts_client.jsapi.get_jsapi_ticket()
        jsapi_agent_ticket = False
        if aid and str(aid) in entry.clients:
            jsapi_agent_ticket = entry.clients[str(
                aid)].jsapi.get_agent_jsapi_ticket()
        timestamp = int(time.time())
        url = request.httprequest.base_url.lower().replace('http://', 'https://')

        context = request.env['ir.http'].webclient_rendering_context()
        context.update({
            'website_domain': request.website.domain,
            'base_url': url,
            'ww_js_options': {
                'app_id': entry.app_id,
                'agent_id': str(aid) if aid else '',
                'nonce_str': nonce_str,
                'timestamp': timestamp,
                'signature': entry.contacts_client.jsapi.get_jsapi_signature(
                    nonce_str, jsapi_ticket, timestamp, url),
                'agent_signature': '' if not jsapi_agent_ticket else entry.clients[aid].jsapi.get_jsapi_signature(
                    nonce_str, jsapi_agent_ticket, timestamp, url),
                'apilist': ['selectExternalContact', 'getCurExternalContact'],
            },

        })
        response = request.render(
            'wechat.wechat_work_test', qcontext=context)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route(['/wechat/work/retrieve_answer_token'], type='json', auth="user", website=True)
    def retrieve_answer_token(self, external_user_open_id, **kwargs):
        external_user = request.env['wechat.work.external.user'].search(
            [('open_id', '=', external_user_open_id)])
        if external_user.exists():
            return {
                'name': external_user.partner_id.name,
                'union_id': external_user.partner_id.union_id,
                'answer_token': _retrieve_answer_token(external_user.partner_id.union_id)
            }
            
    @http.route(['/wechat/list'], type='http', auth="user", website=True)
    def work_list(self, **kwargs):
        wechat_work, entry = request.env['wechat.work.config'].retrieve_entry(
            request.website.company_id.id)
        return json.dumps(entry.clients['1000005'].agent.get('1000005'), ensure_ascii=False)
