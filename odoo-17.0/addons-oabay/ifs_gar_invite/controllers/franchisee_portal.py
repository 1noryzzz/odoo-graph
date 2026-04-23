# -*- coding: utf-8 -*-

import base64
import json
import datetime
from functools import reduce
from operator import ge
from odoo.exceptions import ValidationError, UserError

from odoo import http, _, fields
from odoo.http import request

from odoo.addons.portal.controllers import portal


class FranchiseePortal(portal.CustomerPortal):
    @http.route('/ifs_gar_invite/franchisee/register', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _register(self, **kw):
        return request.render('ifs_gar_invite.ifs_gar_invite_franchisee_register_template', {})

    @http.route('/ifs_gar_invite/new/franchisee/register/basic', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _register_basic(self, business_license=False, **kw):
        if request.httprequest.method == 'POST':
            if business_license:
                franchisee = request.env['ifs.partner.franchisee'].search(
                    [('business_id.company_id', '=', request.env.company.id)])
                franchisee.write({
                    "deposit_license": base64.encodebytes(kw.get('deposit_license').read())
                })
                franchisee.business_id.write({
                    'business_license': base64.encodebytes(business_license.read())
                })

            if kw:
                company_account = request.env['res.company.account'].search(
                    [('company_id', '=', request.env.company.id)])
                if company_account.exists():
                    company_account.write({
                        'account_no': kw.get('account_no'),
                        'name': kw.get('account_name'),
                        'deposit_bank': kw.get('deposit_bank'),
                    })
                else:
                    request.env['res.company.account'].create({
                        'account_no': kw.get('account_no'),
                        'name': kw.get('account_name'),
                        'deposit_bank': kw.get('deposit_bank'),
                        'account_type': 'corp',
                        'company_id': request.env.company.id
                    })

        return request.render('ifs_gar_invite.ifs_gar_invite_franchisee_register_basic_new_template', {})

    @http.route('/ifs_gar_invite/new/franchisee/register/retrieve_idcard', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _retrieve_idcard(self, idcard_front_image, idcard_back_image):
        idcard_front_base64 = base64.encodebytes(idcard_front_image.read())
        idcard_back_base64 = base64.encodebytes(idcard_back_image.read())
        
        ExternalApi = request.env['galaxy.external.api'].sudo()
        face_resp = ExternalApi.invoke('ALY-YSWZSB-SFZSB', body={
            'image': idcard_front_base64.decode(),
            'configure': {'side': 'face'}
        }).retrieve_response('FACE')
        back_resp = ExternalApi.invoke('ALY-YSWZSB-SFZSB', body={
            'image': idcard_back_base64.decode(),
            'configure': {'side': 'back'}
        }).retrieve_response('BACK')
        check_resp = ExternalApi.invoke('ALY-SFZEYS', body={
            'id_number': face_resp.raw.get('num'),
            'name': face_resp.raw.get('name'),
        }).retrieve_response('CHECK')
        
        if check_resp.raw.get('state'):
            res_employee_idcard = request.env['hr.employee.idcard'].sudo().create({
                'name': face_resp.raw.get('name'),
                'idcard_no': face_resp.raw.get('num'),
                'nationality': face_resp.raw.get('nationality'),
                'gender': face_resp.raw.get('sex'),
                'birthday': face_resp.raw.get('birth'),
                'address': face_resp.raw.get('address'),
                'authority': back_resp.raw.get('issue'),
                'start_date': back_resp.raw.get('start_date'),
                'end_date': back_resp.raw.get('end_date'),
                'front_image': idcard_front_base64,
                'back_image': idcard_back_base64,
            })

        idcard_info = json.dumps({
            'name': res_employee_idcard.name,
            'gender': face_resp.raw.get('sex'),
            'birthday': str(res_employee_idcard.birthday),
            'card_no': res_employee_idcard.idcard_no,
            'family_address': res_employee_idcard.address,
            'idcard_expiry_date': str(res_employee_idcard.start_date) + _(" 至 ") + str(res_employee_idcard.end_date),
            'authority': res_employee_idcard.authority,
        }, ensure_ascii=False)

        return str(idcard_info)

    @http.route('/ifs_gar_invite/new/franchisee/register/business', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _register_business(self, **kw):
        franchisee = request.env['ifs.partner.franchisee'].search(
            [('business_id.company_id', '=', request.env.company.id)])
        if not franchisee.exists():
            invite_franchisee = request.env['ifs.gar.invite.franchisee'].search(
                [('business_id.company_id', '=', request.env.company.id)])
            invite_franchisee.start_entry_portal()
            franchisee = invite_franchisee.franchisee_id

        return request.render('ifs_gar_invite.ifs_gar_invite_franchisee_register_business_new_template', {
            'business': franchisee.business_id,
        })

    @http.route('/ifs_gar_invite/new/franchisee/register/other', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _register_other(self, **kw):
        if kw:
            franchisee = request.env['ifs.partner.franchisee'].search(
                [('business_id.company_id', '=', request.env.company.id)])
            franchisee.write({
                'family_address': kw.get('family_address')
            })

        return request.render('ifs_gar_invite.ifs_gar_invite_franchisee_register_other_new_template', {})

    @http.route('/ifs_gar_invite/franchisee/action_and_goto_sign', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def _action_sign(self, **kw):
        franchisee = request.env['ifs.partner.franchisee'].sudo().search(
            [('business_id.company_id', '=', request.env.company.id)])

        businessDoc = request.env['res.company.business.doc']
        businessDoc.update_doc(franchisee.business_id.id, 'reception', base64.encodebytes(
            kw.get('reception').read()))
        businessDoc.update_doc(franchisee.business_id.id, 'office_area', base64.encodebytes(
            kw.get('office_area').read()))

        upload_img_list = self._ums_Image_upload([
            {
                "name": "营业执照",
                "document_type": "0002",
                "img": franchisee.business_license
            },
            {
                "name": "法人身份证",
                "document_type": "0001",
                "img": franchisee.idcard.idcard_front_image
            },
            {
                "name": "身份证反面",
                "document_type": "0011",
                "img": franchisee.idcard.idcard_back_image
            },
            {
                "name": "开户许可证",
                "document_type": "0006",
                "img": franchisee.deposit_license
            },
            {
                "name": "门头照片",
                "document_type": "0005",
                "img": franchisee.reception_picture
            },
            {
                "name": "室内照片",
                "document_type": "0015",
                "img": franchisee.office_area_picture
            },
        ])

        bank_list_resp = self._ums_branch_bank_list({
            "areaCode": "4403",
            "key": franchisee.deposit_bank,
        })

        complex_upload_resp = self._ums_complex_upload({
            "reg_mer_type": "00",
            "legal_name": franchisee.legal_person,
            "legal_idcard_no": franchisee.idcard.card_no,
            # "legal_mobile": franchisee.principal_id.phone,
            # "legal_email": franchisee.principal_id.email,
            "legal_mobile": "16688888888",
            "legal_email": "16688888888@139.com",
            "legal_card_deadline": franchisee.idcard.end_date.strftime("%Y-%m-%d"),
            "legal_sex": 1 if franchisee.principal_id.gender == "male" else 2,
            "legal_occupation": 3,
            "legalmanCareerDesc": "",
            "shop_name": franchisee.business_id.name,
            "bank_no": bank_list_resp.get("branchBankList", [])[0].get("code", ""),
            "bank_acct_type": "1",
            "bank_acct_no": franchisee.account_no,
            "bank_acct_name": franchisee.account_name,
            "shop_province_id": "44",
            "shop_city_id": "4403",
            "shop_country_id": "440303",
            "shop_addr_ext": franchisee.business_id.address,
            "shop_lic": franchisee.business_id.credit_no,
            "mccCode": "5814",
            "product": [{
                "product_id": "8",
                "receipt2Line": "1"
            }],
            "having_fixed_busi_addr": 1,
            "shareholderName": franchisee.legal_person,
            "shareholderCertno": franchisee.idcard.card_no,
            "shareholderCertExpire": franchisee.idcard.end_date.strftime("%Y-%m-%d"),
            "shareholderCertType": "1",
            "shareholderHomeAddr": franchisee.family_address,
            "legalmanHomeAddr": franchisee.family_address,
            "pic_list": upload_img_list
        })

        sign_resp = self._ums_agreement_sign({
            "ums_reg_id": complex_upload_resp.get("ums_reg_id", "")
        })

        return str(sign_resp)

    def _ums_agreement_sign(self, kw):
        request_param = {
            "service": "agreement_sign",
            "accesser_id": "rongcui",
            "sign_type": "SHA-256",
            "request_date": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S%f"),
            "request_seq": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S"),
            "ums_reg_id": kw.get("ums_reg_id", ""),
            "pcOrH5": "PC"
        }
        resp = self._ums_request_query_invoke(
            'ums-agreement_sign', request_param).retrieve_response('resp').raw

        return resp

    def _ums_complex_upload(self, kw):
        request_param = {
            "service": "complex_upload",
            "accesser_id": "rongcui",
            "sign_type": "SHA-256",
            "request_date": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S%f"),
            "request_seq": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S"),
            "accesser_user_id": "rongcui",
            "fax": "",
            "lastTerminalManager": "",
            "lastClientManager": "",
            "serviceDistrict": "",
            "detailDistrict": "",
            "developingDept": "",
            "developingPersonID": "",
            "bnfList": [],
            "remark": "",
            "ums_qrcode_list": "",
            "mchntType": "0",
        }
        request_param.update(kw)

        resp = self._ums_request_body_invoke(
            'ums-complex_upload', request_param).retrieve_response('resp').raw

        return resp

    def _ums_branch_bank_list(self, kw):
        request_param = {
            "service": "branch_bank_list",
            "accesser_id": "rongcui",
            "sign_type": "SHA-256",
            "request_date": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S%f"),
            "request_seq": (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S"),
            "areaCode": kw.get("areaCode", ""),
            "key": kw.get("key", ""),
        }

        resp = self._ums_request_body_invoke(
            'ums-branch_bank_list', request_param).retrieve_response('resp').raw

        return resp

    def _ums_Image_upload(self, imgList):
        img_list_resp = []
        for imgObj in imgList:
            pic_base64 = 'data:image/png;base64,' + \
                imgObj.get("img", "").decode()
            request_param = {
                'service': 'pic_upload',
                'accesser_id': 'rongcui',
                'sign_type': 'SHA-256',
                'request_date': (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S%f"),
                'request_seq': (datetime.datetime.utcnow()+datetime.timedelta(hours=8)).strftime("%Y%m%d%H%M%S"),
                'pic_base64': pic_base64
            }
            resp = self._ums_request_body_invoke(
                'ums-Image-upload', request_param).retrieve_response('resp').raw
            img_list_resp.append({
                "document_name": imgObj.get("name", ""),
                "file_path": resp.get("file_path", ""),
                "file_size": resp.get("file_size", ""),
                "document_type": imgObj.get("document_type", "")
            })

        return img_list_resp

    def _ums_request_body_invoke(self, api_code, request_param):
        body = self._get_ums_request_data(request_param)
        resp = request.env['galaxy.external.api'].sudo().invoke(
            api_code, body=body)

        return resp

    def _ums_request_query_invoke(self, api_code, request_param):
        query_param = self._get_ums_request_data(request_param)
        resp = request.env['galaxy.external.api'].sudo().invoke(
            api_code, query=query_param)

        return resp

    def _get_ums_request_data(self, request_param):
        json_data_str = json.dumps(request_param)
        desStr = request.env['galaxy.external.api.auth.ums.ak'].des3_encrypt(
            'udik876ehjde32dU61edsxsf', json_data_str)
        signedStr = request.env['galaxy.external.api.auth.ums.ak']._sha256hex(
            json_data_str)

        return {
            'json_data': desStr,
            'sign_data': signedStr,
            "accesser_id": "rongcui",
        }
