# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
import json
import requests
import base64
import fitz
import PyPDF2
from PyPDF2 import PdfFileReader
from PIL import Image
import io

from urllib.parse import quote, urlparse

from odoo import Command, _, fields
from odoo.http import Controller, request, route
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
merchant_fields = ['category', 'medical_insurance', 'business_address', 'phone']
merchant_legal_fields = ['name', 'phone','id_card_no', 'handle_image']
emergency_fields = ['name', 'relationships', 'phone']
guarantor_fields = ['name', 'phone','id_card']

supplier_fields = ['seq_code', 'email', 'phone', 'product_scope', 'finance_name', 'finance_phone', 'deposit_bank', 'acc_number', 'logo']
supplier_legal_fields = ['name', 'email', 'phone', 'id_card']
supplier_attachment_fields = ['deposit_license', 'reception_picture', 'office_area_picture']

class OpenApiController(Controller):
    
    @route(['/text_message'], auth="public", cors="*", methods=['GET'])
    def text_message(self,):
        open_app_id = request.env['galaxy.open.api.app'].sudo().browse(4)
        request.env['ifs.message'].sudo().trigger_push(open_app_id,'approval',{'result':'ok'})
        return '1'

        
    @route(['/openapi/entry/merchant_state'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def entry_merchant_state(self, entry_code):
        if not entry_code and not isinstance(entry_code,str):
            raise UserError('参数错误')
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code','=',entry_code)])
        if not entry_merchant.exists():
            raise UserError('进件记录不存在')
        info_dict = {
            'merchant_info': entry_merchant.business_info,
            'legal_info': entry_merchant.legal_info or entry_merchant.guarantor_info,
            'emergency_contact': entry_merchant.legal_other_info,
            # 'attachment_info': entry_merchant.history_order_url
        }
        if entry_merchant.business_type == 'others':
            info_dict['practice_license_info'] = entry_merchant.practice_code
        empty_list = [key for key, value in info_dict.items() if not value]
        result = {
            'entry_code':entry_code,
            'state':entry_merchant.state,
            'account_info':None,
            'empty_list':empty_list,
        }
        if entry_merchant.state == 'rejected':
            result['hint'] = entry_merchant.reject_reason_simple
        elif entry_merchant.state == 'btw':
            result['hint'] = entry_merchant.btw_reason_simple or '资料不完整'
        elif entry_merchant.state == 'committed':
            result['hint'] = ''

        return result
    
    @route(['/openapi/entry/business_license_ocr'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def business_license_ocr(self, image_url, entry_code=False):
        if not image_url:
            raise UserError(_('营业执照参数不能为空！'))
        business_license_info = self.read_binary_data(image_url, '营业执照')
        Config = request.env['ir.config_parameter'].sudo()
        is_verification = Config.get_param(
                'ifs_base.verification_business_license', False)
        reg_ocr_api_code = Config.get_param(
            'ifs_base.business_reg_ocr_api_code', 'ALY-ALYSC-YYZZXXSB')
        business_info = request.env['galaxy.external.api'].sudo().invoke(
            reg_ocr_api_code, body={'image': image_url}).retrieve_response('BUSINESS_INFO', False)
        business_data = business_info and business_info.raw
        if not business_data:
            raise UserError(_("营业执照识别失败，请检查营业执照是否清晰或联系管理员！"))
        if entry_code:
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
            if not entry_merchant:
                raise UserError(_('未找到对应的进件记录，请检查上传的序号是否有误！'))
            if entry_merchant.state not in ['draft', 'btw', 'committed']:
                raise UserError(_('该进件记录在当前状态下不可修改资料！'))
            if is_verification and (
                business_data.get('name') != entry_merchant.name
                    or business_data.get('reg_num') != entry_merchant.company_registry):
                raise UserError(_("营业执照识别信息与根据序号查询到的公司信息不一致，请检查营业执照是否清晰或序号是否有误！"))
            else:
                entry_merchant.ifs_company_id.update({
                    'business_address': business_data.get('address'),
                    'street': business_data.get('address'),
                    'legal_name': business_data.get('person'),
                    'business_license': business_license_info,
                    'business_type': 'company'
                })
                entry_merchant.write({
                    'business_license': business_license_info,
                })
        else:
            ifs_company_id = request.env['ifs.base.company'].sync_business_registration({
                'name':business_data.get('name'),
                'company_registry': business_data.get('reg_num'),
                'business_address':business_data.get('address'),
                'street': business_data.get('address'),
                'business_license': business_license_info
            })
            ifs_company_id.business_type = 'company'
            entry_merchant = self.create_entry_merchant(ifs_company_id)
            entry_code = entry_merchant.seq_code
        return {
            'entry_code': entry_code,
            'business_info': {
                "company_name": business_data.get('name'),
                "credit_no": business_data.get('reg_num'),
                "legal_name": business_data.get('person'),
                "type": business_data.get('type'),
                "establish_date": business_data.get('establish_date'),
                "valid_date": business_data.get('valid_period'),
                "capital": business_data.get('capital'),
                "address":  business_data.get('address'),
                "business_scope": business_data.get('business')
            }
        }
    
    @route(['/openapi/entry/practice_license_ocr'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def practice_license_ocr(self, image_url, entry_code=False):
        if not image_url:
            raise UserError(_('医疗机构执业许可证参数不能为空！'))
        if not entry_code:
            raise UserError(_('进件编号参数不能为空！'))

        practice_license_info = self.read_binary_data(image_url, '医疗机构执业许可证')
        Config = request.env['ir.config_parameter'].sudo()
        is_verification = Config.get_param(
                'ifs_base.verification_business_license', False)

        parsed = urlparse(image_url)
        encoded_path = quote(parsed.path.encode('utf-8'))
        encoded_query = quote(parsed.query.encode('utf-8'), safe='=&')
        encoded_url = parsed._replace(path=encoded_path, query=encoded_query).geturl()
    
        practice_info = request.env['galaxy.external.api'].sudo().invoke(
            'ALY-ALYSC-YLJGZYXKZ', body={'IMAGE': encoded_url, 'IMAGE_TYPE': 1}).retrieve_response('HQYLJGZYXKZXX', False)
        practice_raw = practice_info.raw
        if not (practice_info and practice_raw):
            raise UserError(_("医疗机构执业许可证识别失败，请检查医疗机构执业许可证是否清晰或联系管理员！"))
        if entry_code:
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
            if not entry_merchant:
                raise UserError(_('未找到对应的进件记录，请检查上传的序号是否有误！'))
            if entry_merchant.state not in ['draft', 'btw', 'committed']:
                raise UserError(_('该进件记录在当前状态下不可修改资料！'))
            if is_verification and (
                practice_raw.get('机构名称') != entry_merchant.name
                    or practice_raw.get('登记号') != entry_merchant.practice_code):
                raise UserError(_("医疗机构执业许可证识别信息与根据进件编号查询到的公司信息不一致，请检查医疗机构执业许可证是否清晰或序号是否有误！"))
            entry_merchant.ifs_company_id.update({
                # 'legal_name': practice_raw.get('法定代表人'),
                # 'business_address': practice_raw.get('地址'),
                # 'street': practice_raw.get('地址'),
                'practice_code': practice_raw.get('登记号'),
                'practice_definition_id': practice_info.definition_id.id,
                'practice_license': practice_license_info,
                'practice_raw': practice_raw,
                'business_type': 'others'
            })
                
        else:
            ifs_company_id = request.env['ifs.base.company'].search([('name', '=', practice_raw.get('机构名称'))])
            if ifs_company_id:
                if ifs_company_id.company_id.ifs_partners:
                    raise UserError(_('当前公司已存在系统且已有参与方角色，请检查许可证上传是否有误，如果要对该公司的许可证信息做更新，请上传entry_code参数！'))
                else:
                    ifs_company_id.update({
                        'legal_name': practice_raw.get('法定代表人'),
                        'business_address': practice_raw.get('地址'),
                        'street': practice_raw.get('地址'),
                        'practice_code': practice_raw.get('登记号'),
                        'practice_definition_id': practice_info.definition_id.id,
                        'practice_license': practice_license_info,
                        'practice_raw': practice_raw,
                    })
                
            else:
                legal_person = request.env['res.partner'].create({
                    'name': practice_raw.get('法定代表人'),
                })
                ifs_company_id = request.env['ifs.base.company'].sudo().create({
                    'name':practice_raw.get('机构名称'),
                    'business_address':practice_raw.get('地址'),
                    'street': practice_raw.get('地址'),
                    'legal_id': legal_person.id,
                    'principal_id': legal_person.id,
                    'practice_code': practice_raw.get('登记号'),
                    'practice_definition_id': practice_info.definition_id.id,
                    'practice_license': practice_license_info,
                    'practice_raw': practice_raw,
                })
            ifs_company_id.business_type = 'others'
            entry_merchant = self.create_entry_merchant(ifs_company_id)
            entry_code =  entry_merchant.seq_code
        establish_date = None
        valid_date = None
        if practice_raw.get('有效期限自') is not None and practice_raw.get('有效期限自') != '':
            establish_date = practice_raw.get('有效期限自')
            establish_date = establish_date.replace('年','').replace('月','').replace('日','')
        if practice_raw.get('有效期限至') is not None and practice_raw.get('有效期限至') != '':
            valid_date = practice_raw.get('有效期限至')
            valid_date = valid_date.replace('年','').replace('月','').replace('日','')
        return {
            'entry_code': entry_code,
            'permission_info': {
                "company_name": practice_raw.get('机构名称'),
                "reg_no": practice_raw.get('登记号'),
                "legal_name": practice_raw.get('法定代表人'),
                "principal_name": practice_raw.get('主要负责人'),
                "establish_date": establish_date,
                "valid_date":valid_date,
                "address": practice_raw.get('地址'),
                "business_scope": practice_raw.get('诊疗科目'),
            }
        }
        
    @route(['/openapi/entry/trade_license_ocr'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def trade_license_ocr(self, entry_code, image_url):
        if not entry_code:
            raise UserError(_('进件编号参数不能为空！'))
        if not image_url:
            raise UserError(_('药品经营许可证参数不能为空！'))
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
        if not entry_merchant:
            raise UserError(_('未找到对应的进件记录，请检查上传的进件编号是否有误！'))
        if entry_merchant.state not in ['draft', 'btw', 'committed']:
            raise UserError(_('该进件记录在当前状态下不可修改资料！'))
        trade_license_info = self.read_binary_data(image_url, '药品经营许可证')

        parsed = urlparse(image_url)
        encoded_path = quote(parsed.path.encode('utf-8'))
        encoded_query = quote(parsed.query.encode('utf-8'), safe='=&')
        encoded_url = parsed._replace(path=encoded_path, query=encoded_query).geturl()

        license_info = request.env['galaxy.external.api'].sudo().invoke(
            'ALY-ALYSC-YPJYXKZSB', body={'IMAGE': encoded_url, 'IMAGE_TYPE': 1}).retrieve_response('HQYPJYXKZXX', False)
        license_raw = license_info and license_info.raw
        if not license_raw:
            entry_merchant.update({
                'trade_license': trade_license_info,
            })
        else:
            entry_merchant.update({
                'trade_license': trade_license_info,
                'trade_license_code': license_raw.get('许可证编号'),
            })
        return {
            'entry_code': entry_code,
            'permission_info': {
                'company_name': license_raw.get('企业名称') if license_raw else '',
                'reg_no': license_raw.get('许可证编号') if license_raw else '',
                'type': license_raw.get('经营方式') if license_raw else '',
                'legal_name': license_raw.get('法定代表人') if license_raw else '',
                'principal_name': license_raw.get('企业负责人') if license_raw else '',
                'qa_name': license_raw.get('质量负责人') if license_raw else '',
                'address': license_raw.get('注册地址') if license_raw else '',
                'repo_address': license_raw.get('仓库地址') if license_raw else '',
            }
        }
    
    @route(['/openapi/entry/idcard_ocr'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def idcard_ocr(self, entry_code, use, face_image_url, back_image_url, phone):
        if not (face_image_url and back_image_url):
            raise UserError(_('证件参数不能为空！'))
        
        # 获取法人身份证信息
        face_image = self.read_binary_data(face_image_url, '身份证人像面')
        back_image = self.read_binary_data(back_image_url, '身份证国徽面')
        idcard_info = self.read_idcard_info_url(face_image_url, back_image_url)
        
        # 法人身份证信息
        idcard = self.create_hr_idcard(idcard_info, face_image, back_image)
        if entry_code:
            if not (use and phone):
                raise UserError(_('身份证用途或手机号参数不能为空！'))
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
            if not entry_merchant:
                raise UserError(_('未找到对应的进件记录，请检查上传的进件编号是否有误！'))
            if entry_merchant.state not in ['draft', 'btw', 'committed']:
                raise UserError(_('该进件记录在当前状态下不可修改资料！'))
            # employee = request.env['ifs.partner.merchant'].sudo().search([('root_employee_id.identification_id', '=', idcard.idcard_no)])
            # if employee:
            #     raise UserError(_('当前该人员已经成为公司负责人，一个人只能成为一家公司的负责人！'))
            if use == 'principal':# or entry_merchant.business_type == 'others':
                entry_merchant.update({
                    'guarantor_front_image': idcard.front_image,
                    'guarantor_back_image': idcard.back_image,
                    'guarantor_name': idcard.name,
                    'guarantor_idcard_no': idcard.idcard_no,
                    'guarantor_nationality': idcard.nationality,
                    'guarantor_gender': idcard.gender,
                    'guarantor_birthday': idcard.birthday,
                    'guarantor_address': idcard.address,
                    'guarantor_authority': idcard.authority,
                    'guarantor_start_date': idcard.start_date,
                    'guarantor_end_date': idcard.end_date,
                    'is_self_guarantee': False
                })
            # 担保人身份证信息
            elif use == 'legal':
                Config = request.env['ir.config_parameter'].sudo()
                is_verification_name = Config.get_param(
                    'ifs.gar.entry.verification.legalperson.name')
                if is_verification_name and entry_merchant.ifs_company_id.legal_name != idcard_info.get('name'):
                    raise UserError(_("法人身份证信息与根据序号查询到的公司法人信息不一致，请检查身份证是否清晰或序号是否有误！"))
                entry_merchant.update({
                    'legal_front_image': idcard.front_image,
                    'legal_back_image': idcard.back_image,
                    'legal_name': idcard.name,
                    'legal_id_number': idcard.idcard_no,
                    'legal_nationality': idcard.nationality,
                    'legal_gender': idcard.gender,
                    'legal_birthday': idcard.birthday,
                    'legal_address': idcard.address,
                    'legal_authority': idcard.authority,
                    'legal_start_date': idcard.start_date,
                    'legal_end_date': idcard.end_date,
                    'is_self_guarantee': True # 法人进件，这个值此时用来标识是否需要单位授权书
                })

                auth_res_json = request.env['galaxy.external.api'].sudo().invoke(
                    "AUTHENTI-CATIONREAL-PERSINFO",
                    body={
                        'fullName': idcard.name,
                        'identityCard': idcard.idcard_no,
                    },
                    files={
                        'idenFront': self._compress_image_if_needed(idcard.front_image, force_raw = True),
                        'idenReverse': self._compress_image_if_needed(idcard.back_image, force_raw = True),
                    }).retrieve_response("AUTHENTI-CATIONREAL-PERSINFO-RESULT", True).raw

                auth_ps_json = request.env['galaxy.external.api'].sudo().invoke(
                    "JZQ_TJSQR",
                    body={
                        'email': entry_merchant.jzq_account,
                        'authorizeName': idcard.name,
                        'authorizeMobilePhone': phone,
                        'authorizeCard': idcard.idcard_no
                    }).retrieve_response("JZQ_TJSQR-RESULT", True).raw
            else:
                raise UserError(_('use参数错误！'))
            # 创建根用户
            if not entry_merchant.root_employee_id:
                default_wp = request.env['ifs.work.position'].sudo().search([
                    ('company_id', '=', entry_merchant.company_id.id),
                    ('code', '=', 'SYSTEM')
                ], limit=1)
                
                user_info = {
                    'name': idcard.name,
                    'login': entry_merchant.ifs_company_id.seq_code,
                    'mobile_phone': phone,
                    'work_phone': phone,
                    'work_email': f'{phone}@139.com',
                    'work_position_ids': [Command.link(default_wp.id)] if default_wp else False,
                    'state': 'normal',
                    'company_id': entry_merchant.company_id.id,
                    'is_root': True,
                    'gender': idcard.gender,
                    'birthday': idcard.birthday,
                    'idcard_id': idcard.id,
                }
                entry_merchant.root_employee_id = request.env['hr.employee'].sudo().create(user_info)
            else:
                is_change = False
                # 进件未完成更换进件人
                if entry_merchant.state != 'draft' and entry_merchant.root_employee_id.sudo().identification_id != idcard.idcard_no:
                    is_change = True
                    # 重新创建合同
                    f41_contract = self.create_contract(entry_merchant, 'F41', {
                        'name': idcard.name,
                        'id_number': idcard.idcard_no,
                    })
                    f42_contract = self.create_contract(entry_merchant, 'F42')
                    f43_contract = self.create_contract(entry_merchant, 'F43')

                    entry_merchant.write({
                        'state': 'draft',
                        'f41_contract_info_id': f41_contract.id,
                        'f42_contract_info_id': f42_contract.id,
                        'f43_contract_info_id': f43_contract.id
                    })
                    
                entry_merchant.root_employee_id.sudo().write({
                    'name': idcard.name,
                    'mobile_phone': phone,
                    'work_phone': phone,
                    'work_email': f'{phone}@139.com',
                    'gender': idcard.gender,
                    'birthday': idcard.birthday,
                    'idcard_id': idcard.id,
                })
                
                if is_change:
                    # 推送通知
                    info_dict = {
                        'merchant_info': entry_merchant.business_info,
                        'legal_info': entry_merchant.legal_info or entry_merchant.guarantor_info,
                        'emergency_contact': entry_merchant.legal_other_info,
                        # 'attachment_info': entry_merchant.history_order_url
                    }
                    if entry_merchant.business_type == 'others':
                        info_dict['practice_license_info'] = entry_merchant.practice_code
                    empty_list = [key for key, value in info_dict.items() if not value]
                    
                    supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
                    if not supplier.exists():
                        raise UserError(_('只有供应方才能修改身份证信息！'))
                    api_app = request.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], order='create_date desc', limit=1)
                    if not api_app:
                        raise UserError(_('没有找到对应的应用！'))
                    sign_token = request.env['ifs.contract.info.sign.token'].prepare_sign(
                        [f41_contract.id, f42_contract.id, f43_contract.id], website_id=request.env.ref('website.default_website').id,
                        sign_partner=entry_merchant, next_state='signed', ref_object=entry_merchant)
                    message_body = {
                        'approval_info': {
                            'entry_code': entry_merchant.seq_code,
                            'state': 'draft',
                            'sign_url': sign_token.sign_url,
                            'empty_list': empty_list,
                            'account_info': None
                        }
                    }  
                    request.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)

            # 写入Saleperson
            entry_merchant.root_employee_id.sudo().user_partner_id.write({
                'user_id': request.env.user.id
            })
        return {
            'entry_code': entry_code if entry_code else None,
            'id_card_info': {
                'name': idcard_info.get('name'),
                'id_card_no': idcard_info.get('id_number'),
                'gender': idcard_info.get('gender'),
                'nationality': idcard_info.get('nationality'),
                'birthday': idcard_info.get('birthday'),
                'authority': idcard_info.get('authority'),
                'start_date': idcard_info.get('start_date'),
                'end_date': idcard_info.get('end_date'),
                'address': idcard_info.get('address'),
            },
        }
        
    def create_contract(self, entry, code, params=False):
        template = request.env['ifs.contract.template'].sudo().retrieve_by_code(
            code, entry.invite_id.factor_id.id, entry.invite_id.supplier_id.id)
        contract = request.env['ifs.contract.info'].sudo().create({
            'name': template.name,
            'template_id': template.id,
            'partner_one': '%s,%d' % (entry._name, entry.id),
        })
        if params:
            contract.params = json.dumps(params)
        return contract
        
    def create_entry_merchant(self,ifs_base_company):
        supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
        if not supplier.exists():
            raise UserError(_('只有供应方才能邀请采购方进件！'))
        factor = supplier.factor_ids[0].factor_id
        invite_merchant = request.env['ifs.gar.invite.merchant'].sudo().search([('ifs_company_id', '=', ifs_base_company.id), ('supplier_id', '=', supplier.id), ('factor_id', '=', factor.id)], limit=1)
        if not invite_merchant.exists():
            invite_merchant = request.env['ifs.gar.invite.merchant'].sudo().create({
                'ifs_company_id': ifs_base_company.id,
                'factor_id': factor.id,
                'supplier_id': supplier.id,
                'invite_date': fields.Datetime.now(),
                'state': 'waiting'
            })
        elif invite_merchant.state in ['tobesign', 'ready']:
            raise UserError(_('当前供应方已邀请该采购方， 请勿重复邀请！'))
        elif invite_merchant.state == 'rejected':
            raise UserError(_('当前受邀方已被禁止加入系统！'))
        else:
            invite_merchant.sudo().write({
                'invite_date': fields.Datetime.now(),
            })
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('ifs_company_id', '=', invite_merchant.ifs_company_id.id), ('invite_id', '=', invite_merchant.id)], order='create_date desc', limit=1)
        if not entry_merchant.exists():
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().create({
                'invite_id': invite_merchant.id,
                'ifs_company_id': invite_merchant.ifs_company_id.id,
                'business_license': invite_merchant.ifs_company_id.business_license,
                'state': 'draft',
                'current_model': 'ifs.gar.entry.merchant.finish.wizard',
                'create_from': 'open_api',
            })
        elif entry_merchant.state in ['approve', 'approval', 'signed']:
            raise UserError(_('当前采购方已经完成或存在正在进行的进件流程，请勿重复进件！'))
        elif entry_merchant.state == 'rejected':
            raise UserError(_('当前采购方已被禁止进件！'))
        return entry_merchant
        
    @route(['/openapi/entry/merchant'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def merchant_entry(self, entry_code, factor_code, reception_picture, office_area_picture, 
                       merchant_info, legal_info, emergency_contact, attachment_info, practice_license_info, bill_info):
        # 校验必填字段是否为空
        if not (entry_code and factor_code and reception_picture and office_area_picture):
            raise UserError(_("必填参数不能为空！"))
        
        # 查询对应进件记录同时判断是否可修改资料
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
        if not entry_merchant.exists():
            raise UserError(_('根据传入的进件编号未找到对应的进件记录，请检查编号是否有误！'))
        if entry_merchant.state not in ['draft', 'btw', 'committed']:
            raise UserError(_('该进件记录在当前状态下不可修改资料！'))
        
        # 校验前置接口补充信息是否完成
        if not (entry_merchant.trade_license or entry_merchant.practice_license):
            raise UserError(_('请补充上传药品经营许可证或医疗机构执业许可证！'))
        # if not (not entry_merchant.company_registry and entry_merchant.practice_code) and not entry_merchant.trade_license:
        #     raise UserError(_('缺少药品经营许可证信息，不可修改资料，请先调用前置接口上传！'))
        if not (entry_merchant.legal_id_number or entry_merchant.guarantor_idcard_no):
            raise UserError(_('缺少进件人身份信息，不可修改资料，请先调用前置接口上传！'))
        
        # 判断当前角色和保理方是否已经进入系统
        supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
        if not supplier.exists():
            raise UserError(_('只有供应方才能邀请采购方进件！'))
        factor = request.env['ifs.partner.factor'].search([('seq_code', '=', factor_code)])
        if not factor.exists():
            raise UserError(_('未找到对应的保理方信息，请检查社会统一信用代码填写是否有误！'))
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].search([('factor_id', '=', factor.id), ('supplier_id', '=', supplier.id)])
        if not factor_supplier.exists():
            raise UserError(_('当前保理方和供应方不存在关联关系，请重新上传！'))
        
        #将下面进行操作的用户改为当前受邀采购方的根用户
        request.update_env(user=entry_merchant.root_employee_id.sudo().user_id.id, context={
            **request.env.context,
            'allowed_company_ids': entry_merchant.root_employee_id.sudo().user_id.company_ids.ids
        })
        request.env.cr.commit()
        #查询更换操作用户以后是否有进件权限
        has_permission = request.env.user.has_group('ifs_gar_invite.group_ifs_gar_merchant_entry')
        if not has_permission:
            raise UserError(_('当前进件采购方的根用户无操作权限，请联系工作人员处理！'))
        
        # 更新店铺收银台和门头照片
        reception_picture = self.read_binary_data(reception_picture, '店铺收银台照片')
        office_area_picture = self.read_binary_data(office_area_picture, '门头照片')
        entry_merchant.update({
            'reception_picture': reception_picture,
            'office_area_picture': office_area_picture,
        })
            
        # 药店基本信息不为空，校验必填字段，更新进件信息
        if merchant_info:
            self.chack_data(merchant_info, merchant_fields)
            phone = merchant_info.get('phone')
            entry_merchant.ifs_company_id.write({
                'logo': self.read_binary_data(merchant_info.get('logo'), '公司logo') if merchant_info.get('logo') else entry_merchant.ifs_company_id.logo,
                'email': merchant_info.get('email') or f'{phone}@139.com',
                'phone': phone,
            })
            
            business_info_definition_id,business_config = self.get_config_info(factor.id, supplier.id, 'QYJYXX', merchant_info)
            entry_merchant.update({
                'business_info_definition_id': business_info_definition_id,
                'business_info': business_config,
            })
            if merchant_info.get('rental'):
                business_info_optional_definition_id,business_info_optional = self.get_config_info(factor.id, supplier.id, 'QYJYXXKX', merchant_info)
                entry_merchant.update({
                    'business_info_optional_definition_id': business_info_optional_definition_id,
                    'business_info_optional': business_info_optional,
                })
        # 法人信息不为空，校验必填字段，更新进件信息
        if legal_info:
            self.chack_data(legal_info, merchant_legal_fields)
            entry_merchant.root_employee_id.sudo().write({
                'work_email': legal_info.get('email') or entry_merchant.root_employee_id.sudo().work_email,
                'mobile_phone': legal_info.get('phone'),
                'work_phone': legal_info.get('phone'),
            })
            handle_image = self.read_binary_data(legal_info.get('handle_image'), '法人手持身份证照片')
            legal_phone = legal_info.get('phone')
            legal_info['email'] = legal_info.get('email') or f'{legal_phone}@139.com'
            if entry_merchant.is_self_guarantee:
                legal_info_definition_id,legal_config = self.get_config_info(factor.id, supplier.id, 'FRXX', legal_info)
                legal_update = (entry_merchant.legal_name and entry_merchant.legal_name != legal_info.get('name')) or (entry_merchant.legal_id_number and entry_merchant.legal_id_number != legal_info.get('id_card_no'))
                if legal_update:
                    raise UserError(_('当前上传的法人信息和身份证识别接口信息不一致，请重新上传！'))
                entry_merchant.update({
                    'legal_info_definition_id': legal_info_definition_id,
                    'legal_info': legal_config,
                    'legal_handle_image': handle_image,
                    'legal_name': legal_info.get('name'),
                    'legal_id_number': legal_info.get('id_card_no')
                })
            else:
                legal_info['guarantor_phone'] = legal_phone
                legal_info['guarantor_email'] = legal_info['email']
                guarantor_info_definition_id,guarantor_config = self.get_config_info(factor.id, supplier.id, 'DBRXX', legal_info)
                guarantor_update = (entry_merchant.guarantor_name and entry_merchant.guarantor_name != legal_info.get('name')) or (entry_merchant.guarantor_idcard_no and entry_merchant.guarantor_idcard_no != legal_info.get('id_card_no'))
                if guarantor_update:
                    raise UserError(_('当前上传的负责人信息和身份证识别接口信息不一致，请重新上传！'))  
                entry_merchant.update({
                    'guarantor_info_definition_id': guarantor_info_definition_id,
                    'guarantor_info': guarantor_config,
                    'legal_handle_image': handle_image,
                    'guarantor_name': legal_info.get('name'),
                    'guarantor_idcard_no': legal_info.get('id_card_no')
                })
        # 紧急联系人信息不为空，校验必填字段，更新进件信息
        if emergency_contact:
            if not isinstance(emergency_contact, list):
                raise UserError('emergency_contact参数类型错误！')
            emergency_info = {}
            if emergency_contact[0]:
                self.chack_data(emergency_contact[0], emergency_fields)
                emergency_info = emergency_contact[0]
            # 联系人有多个的时候，按原有逻辑会取第二个紧急联系人，此处先不取
            # if len(emergency_contact) > 1:
            #     self.chack_data(emergency_contact[1], emergency_fields)
            #     for key, value in emergency_contact[1].items():
            #         emergency_info.update({
            #             key + '_two': value,
            #         })
                
            other_info_definition_id,other_config = self.get_config_info(factor.id, supplier.id, 'QTXGXX', emergency_info)
            entry_merchant.update({
                'legal_other_info_definition_id': other_info_definition_id,
                'legal_other_info': other_config,
            })
        # 公司附件信息不为空，校验必填字段，更新进件信息
        if attachment_info:
            history_order_url = attachment_info.get('history_order_url')
            # if not history_order_url:
            #     raise UserError(_("'历史订单'参数不能为空！"))
            # 若非法人进件，需要提供单位授权书图片
            if not entry_merchant.is_self_guarantee and not attachment_info.get('authorization_letter_url'):
                raise UserError(_("'单位授权书'参数不能为空！"))
            framework_agreement = entry_merchant.framework_agreement
            framework_agreement_preview = entry_merchant.framework_agreement_preview
            if attachment_info.get('agreements'):
                framework_agreement_url = attachment_info.get('agreements').get('framework_agreement_url')
                framework_agreement = self.read_binary_data(framework_agreement_url, 'framework_agreement_url')
                framework_agreement_preview = self.intercept_preview(framework_agreement)
            charter = self.read_binary_data(attachment_info.get('charter_url'), '公司章程') if attachment_info.get('charter_url') else entry_merchant.charter
            charter_preview = self.intercept_preview(charter) if charter else entry_merchant.charter_preview
            lease_contract = self.read_binary_data(attachment_info.get('lease_contract_url'), '租赁合同') if attachment_info.get('lease_contract_url') else entry_merchant.lease_contract
            lease_contract_preview = self.intercept_preview(lease_contract)if lease_contract else entry_merchant.lease_contract
            letter_of_authorization = self.read_binary_data(attachment_info.get('authorization_letter_url'), '单位授权书') if attachment_info.get('authorization_letter_url') else entry_merchant.letter_of_authorization
            entry_merchant.update({
                'history_order_url': history_order_url,
                'charter': charter,
                'charter_preview': charter_preview,
                'lease_contract': lease_contract,
                'lease_contract_preview': lease_contract_preview,
                'letter_of_authorization': letter_of_authorization,
                'framework_agreement': framework_agreement,
                'framework_agreement_preview': framework_agreement_preview,
            })
        # 使用医疗机构执业许可证进件时校验医疗机构执业许可证信息
        if practice_license_info and entry_merchant.business_type == 'others':
            if practice_license_info.get('name') and practice_license_info.get('license_id'):
                # company = request.env['res.company'].sudo().search([('name', '=', practice_license_info.get('name'))])
                # if company.exists() and entry_merchant.ifs_company_id.company_id.id != company.id:
                #     raise UserError(_('公司名称已存在！'))
                entry_merchant.ifs_company_id.update({
                    # 'name': practice_license_info.get('name'),
                    'practice_code': practice_license_info.get('license_id'),
                })
            else:
                raise UserError(_('使用医疗机构执业许可证进件时缺少医疗机构执业许可证信息！'))

        # 进件采购方企业认证
        if entry_merchant.ifs_company_id.org_auth_state!= 'certified':
            entry_merchant.ifs_company_id.sudo().certificate_company()

        info_dict = {
            'merchant_info': merchant_info,
            'legal_info': legal_info,
            'emergency_contact': emergency_contact,
            # 'attachment_info': attachment_info
        }
        if entry_merchant.business_type == 'others':
            info_dict['practice_license_info'] = entry_merchant.practice_code
        empty_list = [key for key, value in info_dict.items() if not value]
            
        api_app = request.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], order='create_date desc', limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用！'))
        
        result_body = {
            'entry_code': entry_merchant.seq_code,
            'approval_info': {
                'empty_list': empty_list
            }
        }
        message_body = {
            'approval_info': {
                'entry_code': entry_merchant.seq_code,
                'empty_list': empty_list,
                'account_info': None
            }
        }    
        # 生成签名url
        if entry_merchant.state == 'draft':
            contract_info_ids = []
            if entry_merchant.f41_contract_info_id:
                contract_info_ids.append(entry_merchant.f41_contract_info_id.id)
            if entry_merchant.f42_contract_info_id:
                contract_info_ids.append(entry_merchant.f42_contract_info_id.id)
            if entry_merchant.f43_contract_info_id:
                contract_info_ids.append(entry_merchant.f43_contract_info_id.id)
            sign_token = request.env['ifs.contract.info.sign.token'].prepare_sign(
                contract_info_ids, website_id=request.env.ref('website.default_website').id,
                sign_partner=entry_merchant, next_state='signed', ref_object=entry_merchant)
            result_body['approval_info'].update({
                'state': 'draft',
                'sign_url': sign_token.sign_url,
            })
            message_body['approval_info'].update({
                'state': 'draft',
                'sign_url': sign_token.sign_url,
            })
            request.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)
        elif entry_merchant.state == 'btw':
            result_body['approval_info'].update({
                'state': 'committed' if not empty_list else 'btw',
                'hint': '' if not empty_list else '资料不完整',
            })
            message_body['approval_info'].update({
                'state': 'committed' if not empty_list else 'btw',
                'hint': '' if not empty_list else '资料不完整',
            })
            if not empty_list:
                entry_merchant.state = 'committed'
                request.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)

                list_type = entry_merchant.business_info.get('list_type')
                if list_type in [10, 30]:
                    entry_merchant.write({
                        'state': 'approve' if list_type == 10 else 'btw',
                        'factor_approval_time': fields.Datetime.now()
                    })

                    message_body = {
                        'approval_info': {
                            'entry_code': entry_merchant.seq_code,
                            'state': entry_merchant.state,
                            'hint': entry_merchant.business_info.get('list_reason') if list_type == 30 else None,
                            'empty_list': [],
                            'account_info': None
                        }
                    }
                    request.env['ifs.message'].sudo().trigger_push(api_app, 'approval', message_body)
                # TEST 测试环境对接时将进件的人工审核全部改为自动审核
                # # 保理审核
                # merchant_auditing = request.env['ifs.gar.review.merchant.auditing.wizard'].sudo().create({
                #     'entry_id': entry_merchant.id,
                #     'factor_approval_opinion_output': 'adopt',
                #     'factor_business_base': 'ad',
                #     'factor_business_risk': 'ad',
                #     'factor_legal_person_risk': 'ad',
                #     'factor_guarantor_name_risk': 'ad',
                #     'factor_other_risk': 'ad',
                #     'factor_approval_opinion': '通过',
                # })
                # merchant_auditing.action_confirm()
                # # 供应方审核
                # merchant_approve = request.env['ifs.gar.review.merchant.approve.wizard'].sudo().create({
                #     'entry_id': entry_merchant.id,
                #     'supplier_approval_opinion_output': 'adopt',
                #     'supplier_business_base': 'ad',
                #     'supplier_business_risk': 'ad',
                #     'supplier_legal_person_risk': 'ad',
                #     'supplier_guarantor_name_risk': 'ad',
                #     'supplier_other_risk': 'ad',
                #     'supplier_approval_opinion': '通过',
                #     'supplier_approval_multiple': 100
                # })
                # merchant_approve.action_confirm()
        else:
            result_body['approval_info'].update({
                'state': 'committed',
            })   
        
        return result_body

    @route(['/openapi/merchant/msg_handler'], type='json', auth="public", cors="*", methods=['POST', 'OPTIONS'])
    def merchant_state_search(self, message_type, message_body):
        print('==openapi==' + message_type + '==' + json.dumps(message_body))
        return {
            'message_type': message_type,
            'message_body': message_body
        }
        
    @route(['/openapi/merchant/credit_sign'], type='http', auth="openapi", cors="*", methods=['Get', 'OPTIONS'], website=True)
    def merchant_credit_sign(self, mak, factor_code):
        entry_merchant = self.search_entry_merchant(mak, factor_code)
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].search([('factor_id', '=', entry_merchant.factor_id.id), ('supplier_id', '=', entry_merchant.supplier_id.id)])
        #将下面进行操作的用户改为当前受邀采购方的根用户
        request.update_env(user=entry_merchant.root_employee_id.sudo().user_id.id, context={
            **request.env.context,
            'allowed_company_ids': entry_merchant.root_employee_id.sudo().user_id.company_ids.ids
        })
        has_permission = request.env.user.has_group('ifs_gar_invite.group_ifs_gar_merchant_entry')
        if not has_permission:
            raise UserError(_('无操作权限！'))
        if not entry_merchant.t18_contract_info_id:
            t18_template = request.env['ifs.contract.template'].retrieve_by_code('T18', entry_merchant.factor_id.id)
            t18_contract = request.env['ifs.contract.info'].create({
                'name': t18_template.name,
                'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
                'partner_two': '%s,%d' % (entry_merchant.factor_id._name, entry_merchant.factor_id.id),
                'partner_two_signature': entry_merchant.factor_id.signature,
                'params': json.dumps({
                    'supplier_name': entry_merchant.supplier_id.name,
                    'product_scope': factor_supplier.product_scope,
                    'approved_quota': entry_merchant.supplier_final_quota,
                    'supplier_sign_date': fields.Date.to_string(
                        factor_supplier.t17_contract_info_id.sign_date),
                }),
                'template_id': t18_template.id,
            })

            entry_merchant.write({
                't18_contract_info_id': t18_contract.id
            })
        contract_info_ids = [entry_merchant.t18_contract_info_id.id]
        entry_approval = request.env['ifs.gar.entry.merchant.approval.info.wizard'].create({
            'entry_id': entry_merchant.id,
            't18_contract_info_id': entry_merchant.t18_contract_info_id.id
        })
        sign_token = request.env['ifs.contract.info.sign.token'].prepare_sign(
            contract_info_ids, website_id=request.env.ref(
                'website.default_website').id,
            sign_partner=entry_merchant,
            next_state='signed', ref_object=entry_approval)
            
        return json.dumps({
            'sign_url': sign_token.sign_url
        })
        
    # 贷后资料补充
    @route(['/openapi/els/merchant'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def supplementary_information_after_loan(self, merchant_code, merchant_info,attachment_info,legal_info=None):
        supplier = request.env['ifs.partner.supplier'].sudo().search([('ifs_company_id.company_id','=',request.env.company.id)])
        if not supplier.exists():
            raise UserError("用户错误！")
        merchant = request.env['ifs.partner.merchant'].sudo().search([('seq_code','=',merchant_code)])
        if not merchant.exists():
            raise UserError(_("商户编号错误！"))
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('ifs_company_id', '=', merchant.ifs_company_id.id)],order="id DESC",limit=1)
        # factor = entry_merchant.factor_id
        history_order_url = attachment_info.get('history_order_url')
        if 'medical_insurance' not in merchant_info:
            raise UserError(_("'医保资质'参数不能为空！"))
        if not history_order_url:
            raise UserError(_("'历史订单'参数不能为空！"))
        self.read_binary_data(history_order_url,"历史订单")
        merchant_info_keys = ['medical_insurance','business_address','phone','email','logo','reception_picture','office_area_picture']
        merchant_info = {key: value for key, value in merchant_info.items() if key in merchant_info_keys and value is not None and value != ''}
        base_company_up = {}
        if merchant_info.get('logo'):
            base_company_up['logo'] = self.read_binary_data(merchant_info.get('logo'), '公司logo')
        if merchant_info.get('email'):
            base_company_up['email'] = merchant_info.get('email')
        if merchant_info.get('phone'):
            base_company_up['phone'] = merchant_info.get('phone')
        if len(base_company_up) > 0:
            entry_merchant.ifs_company_id.write(base_company_up)
            
        reception_picture = self.read_binary_data(
            merchant_info.get('reception_picture'), '店铺收银台照片')
        office_area_picture = self.read_binary_data(
            merchant_info.get('office_area_picture'), '门头照片')
        business_config = entry_merchant.business_info
        business_info_optional = entry_merchant.business_info_optional
        for k,v in business_config.items():
            if k in merchant_info:
                business_config[k] = merchant_info.get(k)
        for k,v in business_info_optional.items():
            if k in merchant_info:
                business_info_optional[k] = merchant_info.get(k)

        entry_merchant.update({
            'history_order_url': history_order_url,
            'business_info': business_config,
            'business_info_optional': business_info_optional,
            'reception_picture': reception_picture,
            'office_area_picture': office_area_picture,
        })
        if legal_info and isinstance(legal_info,dict):
            legal_info = {k:v for k,v in legal_info.items() if k in ['phone','email'] and isinstance(v,str) and len(v)>0}
            if len(legal_info)>0:
                if entry_merchant.is_self_guarantee:
                    legal_config = entry_merchant.legal_info
                    for k,v in legal_config.items():
                        if legal_info.get(k):
                            legal_config[k] = v
                    entry_merchant.sudo().update({
                        'legal_info': legal_config
                    })
                else:
                    guarantor_config = entry_merchant.guarantor_info
                    for k,v in guarantor_config.items():
                        if legal_info.get(k):
                            guarantor_config[k] = legal_info.get(v)
                    entry_merchant.sudo().update({
                        'guarantor_info': guarantor_config
                    })
        return {
            "merchant_code":merchant_code
        }
        

       
    @route(['/openapi/merchant/entry_state'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'], website=True)
    def get_merchant_state(self, merchant_code):
        supplier = request.env['ifs.partner.supplier'].sudo().search([('ifs_company_id.company_id','=',request.env.company.id)])
        if not supplier.exists():
            raise UserError("用户错误！")
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('ifs_company_id.seq_code','=',merchant_code),('invite_id.supplier_id','=',supplier.id)])
        if not entry_merchant.exists():
            raise UserError('采购方不存在')
        api_app = request.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用Owner！'))
        apikey = request.env["res.users.apikeys"].with_user(entry_merchant.root_employee_id.sudo().user_id)._generate('galaxy.open.api', api_app.app_id)
        
        partner = supplier.root_employee_id.sudo().user_id.partner_id
        if not partner:
            raise UserError(_('当前进件的采购方相关联的供应方缺少根用户相关信息！'))  
        prepared = partner.signup_prepare(signup_type="signup", expiration=datetime.now() + timedelta(days=1))
        if not prepared:
            raise UserError(_('查询失败!未获取到供应方登录的Token！'))
        state_info = {
            'merchant_info': {
                'name': entry_merchant.name,
                'phone': entry_merchant.phone,
                'email': entry_merchant.email,
                'company_registry': entry_merchant.company_registry,
                'legal_name': entry_merchant.legal_name,
                'legal_phone': entry_merchant.legal_phone,
                'legal_email': entry_merchant.legal_email,
                'business_address': entry_merchant.business_address,
            },
            'state': entry_merchant.state,
            'message': entry_merchant.factor_approval_opinion,
            'credit_info': {
                'apikey': apikey,
                'factor_code': entry_merchant.factor_id.company_registry,
                'token': partner.signup_token 
            }
        }
        if entry_merchant.state == 'btw':
            state_info.write({
                'btw_reason': entry_merchant.btw_reason,
            })
        if entry_merchant.state == 'rejected':
            state_info.write({
                'reject_reason': entry_merchant.reject_reason,
            })
            
        return state_info

    @route(['/openapi/supplier/entry'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'])
    def supplier_invite(self, supplier_info, legal_info, attachment_info):
        # 此处应为校验平台方是否存在系统，但是平台方相关还未完善，暂时不做校验，改为校验供应方是否存在系统
        supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
        if not supplier.exists():
            raise UserError(_('只有第三方供应链平台才能邀请供应方进件！'))
        self.chack_data(supplier_info, supplier_fields)
        self.chack_data(legal_info, supplier_legal_fields)
        self.chack_data(attachment_info, supplier_attachment_fields)
        cut_off_time = supplier_info.get('cut_off_time')
        total_quota = supplier_info.get('total_quota')
        if not (cut_off_time and isinstance(cut_off_time, (float, int)) and cut_off_time > 0):
            raise UserError(_('日切时间参数错误，请重新上传！'))
        if not (total_quota and isinstance(total_quota, (float, int)) and total_quota > 0):
            raise UserError(_('合作额度参数错误，请重新上传！'))
        
        #将下面进行操作的用户改为当前保理方的根用户
        factor = supplier.factor_ids[0].factor_id
        request.update_env(user=factor.root_employee_id.sudo().user_id.id, context={
            **request.env.context,
            'allowed_company_ids': factor.root_employee_id.sudo().user_id.company_ids.ids
        })
        request.env.cr.commit()
        
        # 创建受邀供应方
        ifs_company_id = request.env['ifs.base.company'].search([('seq_code', '=', supplier_info.get('seq_code'))])
        if not ifs_company_id:
            raise UserError(_('未找到对应的公司，请检查上传的序号是否有误！'))
        ifs_company_id.write({
            'logo': self.read_binary_data(supplier_info.get('logo'), '公司logo') if supplier_info.get('logo') else False,
            'email': supplier_info.get('email'),
            'phone': supplier_info.get('phone'),
        })
        # 查找收费方案
        fee_solution_id = request.env['ifs.gar.partner.fee.solution.ver'].sudo().browse(1)
        
        invite_supplier = request.env['ifs.gar.invite.supplier'].search([('ifs_company_id', '=', ifs_company_id.id), ('factor_id', '=', factor.id)])
        if not invite_supplier.exists():
            invite_supplier = request.env['ifs.gar.invite.supplier'].create({
                'ifs_company_id': ifs_company_id.id,
                'factor_id': factor.id,
                'cut_off_time': cut_off_time,
                'fee_solution_id': fee_solution_id.id,
                'invite_date': fields.Datetime.now(),
                'state': 'waiting'
            })
        elif invite_supplier.state in ['activation', 'ready']:
            raise UserError(_('当前供应方已邀请该采购方， 请勿重复邀请！'))
        else:
            invite_supplier.update({
                'cut_off_time': cut_off_time,
                'fee_solution_id': fee_solution_id.id,
                'invite_date': fields.Datetime.now(),
            })
        
        # 创建T17合同
        contract_info_ids = []
        if not invite_supplier.t17_contract_info_id.id:
            template_id = request.env['ifs.contract.template'].retrieve_by_code('T17', invite_supplier.factor_id.id)
            invite_supplier.t17_contract_info_id = request.env['ifs.contract.info'].sudo().create({
                'name': template_id.name,
                'partner_one': '%s,%d' % (invite_supplier._name, invite_supplier.id),
                'partner_two': '%s,%d' % (invite_supplier.factor_id._name, invite_supplier.factor_id.id),
                'partner_one_signature': False,
                'partner_two_signature': invite_supplier.factor_id.signature,
                'template_id': template_id.id,
                'params': json.dumps({
                    'product_scope': supplier_info.get('product_scope'),
                    'contract_total_quota': supplier_info.get('total_quota')/10000,
                    'fee_solution_contract_content': invite_supplier.fee_solution_id.contract_content,
                }),
            })
        contract_info_ids.append(invite_supplier.t17_contract_info_id.id)
        
        # 创建根用户
        idcard = request.env['hr.employee.idcard'].search([('idcard_no', '=', legal_info.get('id_card'))])
        if not idcard:
            raise UserError(_("未找到对应的法人身份证信息，请检查身份证号填写是否有误或调用'采购方身份证信息识别'接口重新上传！"))
        Config = request.env['ir.config_parameter'].sudo()
        is_verification_name = Config.get_param(
            'ifs.gar.entry.verification.legalperson.name')
        if is_verification_name and ifs_company_id.legal_name != idcard.name:
            raise UserError(_("法人身份证信息与根据序号查询到的公司法人信息不一致，请检查身份证号或序号填写是否有误！"))
        if not invite_supplier.root_employee_id:
            default_wp = request.env['ifs.work.position'].sudo().search([
                ('company_id', '=', invite_supplier.company_id.id),
                ('code', '=', 'SYSTEM')
            ], limit=1)
            
            user_info = {
                'name': invite_supplier.legal_id.name,
                'login': ifs_company_id.seq_code,
                'mobile_phone': legal_info.get('phone'),
                'work_email': legal_info.get('email'),
                'work_position_ids': [Command.link(default_wp.id)] if default_wp else False,
                'state': 'normal',
                'company_id': invite_supplier.company_id.id,
                'user_partner_id': invite_supplier.legal_id.id,
                'is_root': True,
                'gender': idcard.gender,
                'birthday': idcard.birthday,
                'idcard_id': idcard.id,
            }
            invite_supplier.root_employee_id = request.env['hr.employee'].sudo().create(user_info)
            # 写入Saleperson
            invite_supplier.root_employee_id.sudo().user_partner_id.write({
                'user_id': request.env.user.id
            })
        else:
            invite_supplier.root_employee_id.sudo().write({
                'mobile_phone': legal_info.get('phone'),
                'work_email': legal_info.get('email'),
                'gender': idcard.gender,
                'birthday': idcard.birthday,
                'idcard_id': idcard.id,
            })
        #将下面进行操作的用户改为当前受邀供应方的根用户
        request.update_env(user=invite_supplier.root_employee_id.sudo().user_id.id, context={
            **request.env.context,
            'allowed_company_ids': invite_supplier.root_employee_id.sudo().user_id.company_ids.ids
        })
        request.env.cr.commit()
        #查询更换操作用户以后是否有进件权限
        has_permission = request.env.user.has_group('ifs_gar_invite.group_ifs_gar_supplier_entry')
        if not has_permission:
            raise UserError(_('无操作权限！'))
        
        #创建进件供应方
        entry_supplier = request.env['ifs.gar.entry.supplier'].search([('ifs_company_id', '=', ifs_company_id.id), ('invite_id', '=', invite_supplier.id)], order='create_date desc', limit=1)
        if not entry_supplier.exists() or entry_supplier.state == 'rejected':
            entry_supplier = request.env['ifs.gar.entry.supplier'].create({
                'invite_id': invite_supplier.id,
                'ifs_company_id': ifs_company_id.id,
                'state': 'draft',
                'current_model': 'ifs.gar.entry.supplier.finish.wizard',
            })
        elif entry_supplier.state in ['committed', 'approval']:
            raise UserError(_('当前采购方已经完成进件流程，请勿重复进件！'))
        #为进件供应方按照进件步骤将所有信息进行同步
        attachment_data = {}
        for key, value in attachment_info.items():
            attachment = self.read_binary_data(value, key)
            if not attachment:
                raise UserError(_("文件读取失败，请检查链接是否正确或重试！"))
            attachment_data[key] = attachment
        res_bank = request.env['res.bank'].sudo().search([('name', '=', supplier_info.get('deposit_bank'))])
        if not res_bank:
            res_bank = request.env['res.bank'].sudo().create({
                'name': supplier_info.get('deposit_bank'),
            })
        entry_info = {
            'create_from': 'open_api',
            'business_license': ifs_company_id.business_license,
            'business_address': ifs_company_id.business_address,
            'legal_front_image': idcard.front_image,
            'legal_back_image': idcard.back_image,
            'legal_name': idcard.name,
            'legal_id_number': idcard.idcard_no,
            'legal_nationality': idcard.nationality,
            'legal_gender': idcard.gender,
            'legal_birthday': idcard.birthday,
            'legal_address': idcard.address,
            'legal_authority': idcard.authority,
            'legal_start_date': idcard.start_date,
            'legal_end_date': idcard.end_date,
            'acc_number': supplier_info.get('acc_number'),
            'bank_id': res_bank.id,
            'finance_name': supplier_info.get('finance_name'),
            'finance_phone': supplier_info.get('finance_phone'),
            'product_scope': supplier_info.get('product_scope'),
            'total_quota': supplier_info.get('total_quota'),
            
            'deposit_license': attachment_data.get('deposit_license'),
            'reception_picture': attachment_data.get('reception_picture'),
            'office_area_picture': attachment_data.get('office_area_picture'),
        }
        entry_supplier.update(entry_info)
        #进件采购方企业认证
        if ifs_company_id.org_auth_state!= 'certified':
            ifs_company_id.sudo().certificate_company()
            
        if entry_supplier.t21_contract_info_id:
            contract_info_ids.append(entry_supplier.t21_contract_info_id.id)
        if entry_supplier.f42_contract_info_id:
            contract_info_ids.append(entry_supplier.f42_contract_info_id.id)
        if entry_supplier.f43_contract_info_id:
            contract_info_ids.append(entry_supplier.f43_contract_info_id.id)
        sign_token = request.env['ifs.contract.info.sign.token'].prepare_sign(
            contract_info_ids, website_id=request.env.ref('website.default_website').id,
            sign_partner=entry_supplier,next_state='signed', ref_object=entry_supplier)
        return {
            'sign_url': sign_token.sign_url
        }
        
    @route(['/openapi/supplier/entry_state'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'], website=True)
    def get_supplier_state(self, supplier_code):
        # 此处应为校验平台方是否存在系统，但是平台方相关还未完善，暂时不做校验，改为校验供应方是否存在系统
        supplier = request.env['ifs.partner.supplier'].sudo().search([('company_id','=', request.env.company.id)])
        if not supplier.exists():
            raise UserError("只有第三方供应链平台才能查询供应方进件状态！")
        #将下面进行操作的用户改为当前保理方的根用户
        factor = supplier.factor_ids[0].factor_id
        request.update_env(user=factor.root_employee_id.sudo().user_id.id, context={
            **request.env.context,
            'allowed_company_ids': factor.root_employee_id.sudo().user_id.company_ids.ids
        })
        request.env.cr.commit()
        
        entry_supplier = request.env['ifs.gar.entry.supplier'].sudo().search([('ifs_company_id.seq_code','=',supplier_code), ('invite_id.factor_id','=',factor.id)])
        if not entry_supplier.exists():
            raise UserError('未找到对应的供应方进件记录，请检查上传参数是否有误！')
        state_info = {
            'supplier_info': {
                'name': entry_supplier.name,
                'phone': entry_supplier.phone,
                'email': entry_supplier.email,
                'company_registry': entry_supplier.company_registry,
                'legal_name': entry_supplier.legal_name,
                'legal_phone': entry_supplier.legal_phone,
                'legal_email': entry_supplier.legal_email,
                'business_address': entry_supplier.business_address,
            },
            'state': entry_supplier.state,
        }
        if entry_supplier.state == 'rejected':
            state_info.update({
               'reject_reason': entry_supplier.reject_reason,
            })
            
        return state_info

    def search_entry_merchant(self, mak, factor_code):
        #验证身份
        supplier = request.env['ifs.partner.supplier'].search([('company_id', '=', request.env.company.id)])
        if not supplier.exists():
            raise UserError(_('只有供应方才能获取采购方征信报告！'))
        if not factor_code:
            raise UserError(_('未获取到保理方的社会统一信用代码！'))
        factor = request.env['ifs.partner.factor'].search([('company_registry', '=', factor_code)])
        if not factor.exists():
            raise UserError(_('未找到对应的保理方信息，请检查社会统一信用代码填写是否有误！'))
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].search([('factor_id', '=', factor.id), ('supplier_id', '=', supplier.id)])
        if not factor_supplier.exists():
            raise UserError(_('当前保理方和供应方不存在关联关系，请重新上传！'))
        
        api_app = request.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用Owner！'))
        user_id = request.env["res.users.apikeys"].sudo()._check_credentials(
            'galaxy_token', api_app.app_id, scope='galaxy.open.api', key=mak)
        if not user_id:
            raise UserError(_('没有找到对应的采购方！'))
        user = request.env['res.users'].search([('id', '=', user_id)])
        #查询采购方进件
        invite_merchant = request.env['ifs.gar.invite.merchant'].search([('company_id', '=', user.company_id.id), ('supplier_id', '=', supplier.id), ('factor_id', '=', factor.id), ('state', '=', 'tobesign')], limit=1)
        if not invite_merchant:
            raise UserError(_('未查询到该采购方的邀请信息，请确认上传信息是否有误！'))
        entry_merchant = request.env['ifs.gar.entry.merchant'].search([('ifs_company_id', '=', invite_merchant.ifs_company_id.id), ('invite_id', '=', invite_merchant.id), ('state', '=', 'approval')], order='create_date desc', limit=1)
        if not entry_merchant:
            raise UserError(_('未查询到该采购方的进件信息，请确认上传信息是否有误！'))
        return entry_merchant
            
    def chack_data(self, datas, fields):
        if datas:
            missing_fields = [field for field in fields if field not in datas or datas.get(field) is None or datas.get(field) == '']
            if len(missing_fields) > 0:
                raise UserError(f'以下必填字段不能为空: {", ".join(missing_fields)}')
        else:
            raise UserError(_('参数不能为空！'))
    
    def read_binary_data(self, url, text):
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content)
        else:
            raise UserError(_(f'获取{text}图片失败,请检查链接是否正确或重试！'))
            
    def read_idcard_info(self, front_image, back_image):
        Config = request.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = request.env['galaxy.external.api']
        idcard_info = {}
        if back_image:
            back_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': back_image.decode('utf-8'),
                'configure': {'side': 'back'}
            }).retrieve_response('BACK')
            idcard_info.update({
                'authority': back_resp.raw.get('issue'),
                'start_date': back_resp.raw.get('start_date'),
                'end_date': back_resp.raw.get('end_date')
            })
        if front_image:
            face_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': front_image.decode('utf-8'),
                'configure': {'side': 'face'}
            }).retrieve_response('FACE')
            check_resp = ExternalApi.invoke(check_api_code, body={
                'id_number': face_resp.raw.get('num'),
                'name': face_resp.raw.get('name'),
            }).retrieve_response('CHECK')

            if check_resp.raw.get('state'):
                idcard_info.update({
                    'id_number': face_resp.raw.get('num'),
                    'name': face_resp.raw.get('name'),
                    'nationality': face_resp.raw.get('nationality'),
                    'gender': face_resp.raw.get('sex'),
                    'birthday': face_resp.raw.get('birth'),
                    'address': face_resp.raw.get('address')
                })
            else:
                raise UserError(_("身份信息认证失败！"))
        return idcard_info

    def read_idcard_info_url(self, front_image_url, back_image_url):
        Config = request.env['ir.config_parameter'].sudo()
        ocr_api_code = Config.get_param(
            'ifs.hr.idcard.ocr.api.code', 'ALY-YSWZSB-SFZSB')
        check_api_code = Config.get_param(
            'ifs.hr.idcard.check.api.code', 'ALY-SFZEYS')
        ExternalApi = request.env['galaxy.external.api']
        idcard_info = {}
        if back_image_url:
            back_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': back_image_url,
                'configure': {'side': 'back'}
            }).retrieve_response('BACK')
            idcard_info.update({
                'authority': back_resp.raw.get('issue'),
                'start_date': back_resp.raw.get('start_date'),
                'end_date': back_resp.raw.get('end_date')
            })
        if front_image_url:
            face_resp = ExternalApi.invoke(ocr_api_code, body={
                'image': front_image_url,
                'configure': {'side': 'face'}
            }).retrieve_response('FACE')
            check_resp = ExternalApi.invoke(check_api_code, body={
                'id_number': face_resp.raw.get('num'),
                'name': face_resp.raw.get('name'),
            }).retrieve_response('CHECK')

            if check_resp.raw.get('state'):
                idcard_info.update({
                    'id_number': face_resp.raw.get('num'),
                    'name': face_resp.raw.get('name'),
                    'nationality': face_resp.raw.get('nationality'),
                    'gender': face_resp.raw.get('sex'),
                    'birthday': face_resp.raw.get('birth'),
                    'address': face_resp.raw.get('address')
                })
            else:
                raise UserError(_("身份信息认证失败！"))
        return idcard_info

    def _compress_image_if_needed(self, image_data, max_size=1024 * 1024, force_raw=False):
        if not image_data:
            return image_data
        _RAW_MAGIC = (b'\xff\xd8', b'\x89PNG', b'GIF8', b'BM')
        _B64_MAGIC = (b'/9j/', b'iVBOR', b'R0lGO', b'Qk==')
        data_bytes = image_data if isinstance(image_data, bytes) else image_data.encode('latin-1')
        if any(data_bytes.startswith(m) for m in _RAW_MAGIC):
            is_raw = True
            raw = data_bytes
        elif any(data_bytes.startswith(m) for m in _B64_MAGIC):
            is_raw = False
            raw = base64.b64decode(data_bytes)
        else:
            try:
                raw = base64.b64decode(data_bytes)
                is_raw = False
            except Exception:
                raw = data_bytes
                is_raw = True
        if len(raw) <= max_size:
            return raw if force_raw else image_data
        img = Image.open(io.BytesIO(raw))
        img = img.convert('RGB')
        quality = 85
        while quality >= 10:
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            compressed = buf.getvalue()
            if len(compressed) <= max_size:
                break
            quality -= 10
        _logger.info('Image compressed to %d bytes (quality=%d)', len(compressed), quality)
        if force_raw:
            return compressed
        return compressed if is_raw else base64.b64encode(compressed)

    def create_hr_idcard(self, idcard_info, front_image, back_image):
        idcard = request.env['hr.employee.idcard'].sudo().search([
            ('idcard_no', '=', idcard_info.get('id_number'))
        ])
        user_info = {
            'name': idcard_info.get('name'),
            'idcard_no': idcard_info.get('id_number'),
            'nationality': idcard_info.get('nationality'),
            'gender': idcard_info.get('gender'),
            'birthday': idcard_info.get('birthday'),
            'address': idcard_info.get('address'),
            'authority': idcard_info.get('authority'),
            'start_date': idcard_info.get('start_date'),
            'end_date': idcard_info.get('end_date') or False,
            'front_image': front_image,
            'back_image': back_image,
        }
        if idcard.exists():
            idcard.write(user_info)
        else:
            idcard = request.env['hr.employee.idcard'].create(user_info)
        return idcard

    def get_config_info(self, factor_id, supplier_id, code, datas):
        details = request.env['ifs.gar.entry.merchant.config'].retrieve_config(
            factor_id, supplier_id, [code])
        detail = details.filtered(lambda c: c.code == code)
        if not detail:
            raise UserError(_(f'未查询到相关可配置区块信息，请确认上传信息是否有误！'))
        definition_id = detail.definition_id
        data = {}
        for definition in definition_id.params_definition:
            if definition.get('type') == 'selection':
                selections = definition.get('selection')
                for selection in selections:
                    if datas.get(definition.get('name')) in selection:
                        data.update({
                            definition.get('name') : selection[0],
                        })
            else:
                data.update({
                    definition.get('name') : datas.get(definition.get('name'), False),
                })
        err_msgs = detail.validate_required(data)
        if len(err_msgs) > 0:
            raise UserError(
                _(f'请填写必填相关信息！包含下列内容：\n\n{"，".join(err_msgs)}'))
        return detail.definition_id.id,data
        
    def intercept_preview(self, data):
        desired_width = 300
        desired_height = 190
        preview_data = False
        with io.BytesIO(base64.b64decode(data)) as pdf_stream:
            pdf_reader = PdfFileReader(pdf_stream)
            if pdf_reader.numPages > 0:
                first_page = pdf_reader.getPage(0)

                # 计算截图的长宽
                new_width = int(first_page.mediaBox[2])
                new_height = int(new_width / (desired_width / desired_height))

                # 使用 PyMuPDF 将 PDF 页面转换为图像
                doc = fitz.open(stream=pdf_stream, filetype="pdf")
                pixmap = doc.load_page(0).get_pixmap()
                pdf_image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

                # 调整图像大小并进行截图
                pdf_image = pdf_image.crop((0, 0, new_width, new_height))
                pdf_image = pdf_image.resize((desired_width * 2, desired_height * 2), Image.ANTIALIAS)

                # 将图像保存为字节流
                image_stream = io.BytesIO()
                pdf_image.save(image_stream, format='JPEG')
                image_stream.seek(0)

                # 将字节流编码为 base64 字符串
                encoded_image = base64.b64encode(image_stream.read())

                # 设置截图字段的值为编码后的图像数据
                preview_data = encoded_image.decode()

            # 关闭 PDF 文件
            doc.close()
            return preview_data