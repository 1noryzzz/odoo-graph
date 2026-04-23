# -*- coding: utf-8 -*-

import odoo

from odoo import _, http
from odoo.http import request
from odoo.addons.website.controllers.main import Website
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class InclusiveFinancingHr(Website):

    @http.route()
    def web_login(self, redirect=None, **kw):
        # if request.httprequest.method == 'POST':
        #     login_user = request.env['res.users'].sudo().search(
        #         [('login', '=', request.params['login'])])
        #     if login_user.exists() and not login_user.login_date:
        #         redirect = '/web/set_password'

        response = super(
            InclusiveFinancingHr, self).web_login(redirect, **kw)

        # if request.httprequest.method == 'GET':
        cfg = request.env['ir.config_parameter'].sudo()
        if cfg.get_param('ifs.hr.otp.global.activated', False):
            response.qcontext['otp_default_invisible'] = cfg.get_param(
                'ifs.hr.otp.default.invisible', False)
        else:
            response.qcontext['otp_default_invisible'] = True

        return response

    @http.route()
    def web_auth_reset_password(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            self.do_signup(qcontext)
            request.params['login'] = qcontext.get('login')
            request.params['password'] = qcontext.get('password')
            return self.web_login(*args, **kw)
        
            # try:
            #     if qcontext.get('token'):
            #         self.do_signup(qcontext)
            #         return self.web_login(*args, **kw)
            #     else:
            #         login = qcontext.get('login')
            #         assert login, _("No login provided.")
            #         _logger.info(
            #             "Password reset attempt for <%s> by user <%s> from %s",
            #             login, request.env.user.login, request.httprequest.remote_addr)
            #         request.env['res.users'].sudo().reset_password(login)
            #         qcontext['message'] = _("An email has been sent with credentials to reset your password")
            # except UserError as e:
            #     qcontext['error'] = e.args[0]
            # except SignupError:
            #     qcontext['error'] = _("Could not reset your password")
            #     _logger.exception('error when resetting password')
            # except Exception as e:
            #     qcontext['error'] = str(e)
        
        response = request.render('ifs_hr.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @http.route(['/ifs_hr/check_need_otp'], type='json', auth="public", website=True)
    def check_need_otp(self, login_name):
        request.update_env(user=odoo.SUPERUSER_ID)
        query_user = request.env['res.users'].search(
            [('login', '=', login_name)])
        return bool(request.env['hr.employee'].is_need_one_time_passwd(query_user.id))

    @http.route(['/ifs_hr/check_login_phone'], type='json', auth="public", website=True)
    def check_login_phone(self, login_phone):
        print(login_phone)
        phone = request.env['res.users'].sudo().search(
            [('partner_id.phone', '=', login_phone)])
        if phone:
            return True
        else:
            raise UserError(_('未查询到该号码！'))

    @http.route(['/ifs_hr/send_check_code'], type='json', auth="public", website=True)
    def send_check_code(self, login_phone):
        print(login_phone)
        res_user = request.env['res.users'].sudo().search([('partner_id.phone', '=', login_phone)])
        if res_user:
            res_user.mapped('partner_id').signup_prepare(signup_type="reset", expiration=datetime.now() + timedelta(minutes=3))
            sms_tepmlate=request.env["sms.template"].sudo().search([('code','=','HR_SMS_148380455')])
            request.env["sms.sms"].sudo().create({
                'template_id':sms_tepmlate.id,
                'partner_id':res_user.partner_id.id
            }).send()
            
    @http.route(['/ifs_hr/check_code_check'], type='json', auth="public", website=True)
    def check_code_check(self, login_phone, checkcode):
        print(checkcode)
        res_user = request.env['res.users'].sudo().search([('partner_id.phone', '=', login_phone)])
        if res_user:
            token = res_user.partner_id.signup_token
            if token and token == checkcode:
                return True
            else:
               raise UserError(_('验证码错误，请重新输入！')) 
