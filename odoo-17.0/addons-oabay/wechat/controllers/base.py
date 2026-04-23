# -*- coding: utf-8 -*-

from datetime import date, datetime, time
from functools import reduce

import werkzeug

from odoo import http, exceptions
from odoo.http import request
from odoo.loglevels import ustr

from odoo.addons.galaxy_common.controllers.main import GalaxyBase

import logging

_logger = logging.getLogger(__name__)

error_code = {
    -99: '',  # 其他异常
    -2: u'用户名或密码不正确',
    -1: u'服务器内部错误',
    0: u'接口调用成功',
    403: u'禁止访问',
    405: u'错误的请求类型',
    501: u'数据库错误',
    502: u'并发异常，请重试',
    600: u'缺少参数',
    601: u'无权操作:缺少 token',
    602: u'签名错误',
    609: u'token无效',
    700: u'暂无数据',
    701: u'该功能暂未开通',
    702: u'资源余额不足',
    901: u'登录超时',
    902: u'登录超时',  # 不触发授权登录
    300: u'缺少参数',
    400: u'域名错误',
    401: u'该域名已删除',
    402: u'该域名已禁用',
    404: u'暂无数据',
    10000: u'微信用户未注册'
}


class WechatBase(GalaxyBase):
    _WECHAT_AGENT = ['MicroMessenger', 'WeChat', 'wechatdevtools']
    _MOBILE_AGENT = ['Android', 'iPhone', 'iPad', 'iPod', 'Windows Phone', 'MQQBrowser']

    def handle_unknown(self, msg):
        return ''
    
    def res_ok(self, data=None):
        ret = {'code': 0, 'msg': 'success'}
        if data != None:
            ret['data'] = data
        return ret

    def res_err(self, code, data=None):
        ret = {'code': code, 'msg': error_code.get(code) or data}
        if data:
            ret['data'] = data
        return ret

    def _abort(self, code):
        return werkzeug.wrappers.Response(
            'Unknown Error: Application stopped.',
            status=code, content_type='text/html;charset=utf-8')

    @http.route('/wechat/test', type='http', auth="public", website=True, sitemap=False)
    def wechat_base_test(self, **kwargs):
        user_agent = request.httprequest.headers.get('User-Agent')
        if reduce(lambda x, y: x or y, [ua in user_agent for ua in self._WECHAT_AGENT]):
            return 'wechat'
        elif reduce(lambda x, y: x or y, [ua in user_agent for ua in self._MOBILE_AGENT]):
            return 'mobile'
        else:
            return 'pc'
    
    @http.route('/WW_verify_UaBRkdJh8bL7tuzd.txt', type='http', auth="public", website=True, sitemap=False)
    def verify_Rm(self, **kwargs):
        return 'UaBRkdJh8bL7tuzd'
    
    @http.route('/MP_verify_P15sPlAZScUq5l7J.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_MPv(self, **kwargs):
        return 'P15sPlAZScUq5l7J'
    
    @http.route('/MP_verify_C4FXOjWTP4BEeTly.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_MPv(self, **kwargs):
        return 'C4FXOjWTP4BEeTly'
    
    @http.route('/WW_verify_xbymqOlMmd8V2YnC.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_lifewiz(self, **kwargs):
        return 'xbymqOlMmd8V2YnC'
    
    @http.route('/MP_verify_BbfC8oZZeSHlgwIb.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_lifewiz_wx(self, **kwargs):
        return 'BbfC8oZZeSHlgwIb'
    
    @http.route('/WW_verify_WxJRq9rkrzUYqxa9.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_lifewiz(self, **kwargs):
        return 'WxJRq9rkrzUYqxa9'
    
    @http.route('/MP_verify_82GcYrSrk2cljxym.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_guanten(self, **kwargs):
        return '82GcYrSrk2cljxym'
    
    @http.route('/MP_verify_tm1WTUJCIGtoOSYE.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_hpyzbfp(self, **kwargs):
        return 'tm1WTUJCIGtoOSYE'
    
    @http.route('/OoVHBjrycg.txt', type='http', auth='public', website=True, sitemap=False)
    def verify_wapp_inair_switch(self, **kwargs):
        return '73a370beb9e3ba8b9bf9fa80fe438b23'
