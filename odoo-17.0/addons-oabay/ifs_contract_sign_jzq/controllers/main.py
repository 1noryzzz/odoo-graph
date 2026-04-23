# -*- coding: utf-8 -*-

import json
import re
import werkzeug
import logging
from odoo import _, http
from odoo.http import request, request
import hashlib
import base64
_logger = logging.getLogger(__name__)


class InclusiveFinancingContract(http.Controller):

    @http.route('/jzq/handle_message', type='http', auth="public", methods=['POST'], sitemap=False, csrf=False)
    def handle_message(self, **kwargs):
        (serviceUrl, appKey, appSecret) = request.env['ifs.contract.info']._get_param_config()
        method = kwargs.get("method")
        version = kwargs.get("version")
        timestamp = kwargs.get("timestamp")
        data = kwargs.get("data")
        sign = kwargs.get("sign")
        appkey = kwargs.get("appkey")

        sign_str = "data"+data+"method"+method+"version"+version + "timestamp"+timestamp+"appKey"+appkey+"appSecret"+appSecret
        if sign != hashlib.sha1(sign_str.encode('utf-8')).hexdigest():
            return request.make_response(json.dumps({"success":False,"msg":"验签失败"}))


        cb_action_conditions = [
            ('value_from', '=', 'jzq'), ('value_code_ids.value', '=', method)]
        cb_actions = request.env['oa.callback.action'].sudo().search(
            cb_action_conditions)
        result = False
        for cb_action in cb_actions:
            # cb_log = request.env['oa.callback.log'].info(2 ,method,cb_action,kwargs, source=False, target=False)
            ret = cb_action.process(False, kwargs, False)
            if ret:
                result = True
        if result:
            return request.make_response(json.dumps({"success":True}))
        else:
            return request.make_response(json.dumps({"success":False}))
            
            
    @http.route('/test/certificate_company', type='http', auth="public", methods=['GET'])
    def certificate_company(self, **kwargs):
        request.env['ifs.base.company'].browse(4).certificate_company()
        
    @http.route('/contract/refresh_all', type='http', auth="public", methods=['GET'])
    def refresh_all(self, **kwargs):
        contract_list = request.env['ifs.contract.info'].search([('jzq_apply_no','!=',False)])
        for contract in contract_list:
            res_sign_status_data = request.env['galaxy.external.api'].invoke(
                "APP-SGIN-STATUS",
                body={'applyNo': contract.jzq_apply_no,
                      'fullName': contract.full_name,
                      'identityCard': contract.identity_card,
                      'identityType': contract.identity_type}
            ).retrieve_response("APP-SGIN-STATUS-RESULT", False).raw
            res_contact_view_data = request.env['galaxy.external.api'].invoke(
                "APP-LINK-ANONY-DETAIL", body={'applyNo': contract.jzq_apply_no}).retrieve_response("APP-LINK-ANONY-DETAIL-RESULT", False).raw
            res_contact_download_data = request.env['galaxy.external.api'].invoke(
                "APP_DOWNLOADLINK", body={'applyNo': contract.jzq_apply_no}).retrieve_response("APP_DOWNLOADLINK-RESULT", False).raw
            jzq_state = res_sign_status_data.get('data')
            app_link_anony = res_contact_view_data.get('data')
            app_download_link = res_contact_download_data.get('data')
            sign_file = contract._download_file(
                app_download_link, contract.name)
            if sign_file:
                contract.write({
                    'contract': base64.b64encode(sign_file.getvalue()),
                    'jzq_contract_view_url': app_link_anony,
                    'jzq_contract_dl_url': app_download_link,
                    'jzq_state': str(jzq_state),
                })
        return "共更新了{}条数据".format(len(contract_list))