# -*- coding: utf-8 -*-

import logging
import json

from odoo import Command, _, fields
from odoo.http import Controller, request, route
from odoo.exceptions import UserError

from odoo.addons.ifs_gar_entry.controllers.openapi import OpenApiController

_logger = logging.getLogger(__name__)

class OpenApiController(OpenApiController):

    @route(['/list/queryEnterpriseList'], type='http', auth="none", csrf=False)
    def query_enterprise_list(self, **kwargs):
        headers = [("Content-Type", "application/json"), ("Cache-Control", "no-store")]
        data = {
            'success': True,
            'resCode': '000000',
            'resMsg': '成功',
            'data': {
                'customerId': "00000",
                'customerName': json.loads(request.httprequest.get_data(as_text=True)).get('customerName'),
                'listType': 10,
                'source': 20,
                'listReason':  None,
                'addedTime': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        return request.make_response(json.dumps(data), headers)

    @route()
    def merchant_entry(self, entry_code, factor_code, reception_picture, office_area_picture, 
                       merchant_info, legal_info, emergency_contact, attachment_info, practice_license_info, bill_info):
        if not (entry_code and factor_code and reception_picture and office_area_picture):
            raise UserError(_("必填参数不能为空！"))
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
        if not entry_merchant.exists():
            raise UserError(_('根据传入的进件编号未找到对应的进件记录，请检查编号是否有误！'))
        if entry_merchant.state not in ['draft', 'btw', 'committed']:
            raise UserError(_('该进件记录在当前状态下不可修改资料！'))

        ExternalApi = request.env['galaxy.external.api']
        try:
            credit_nl = ExternalApi.invoke("YYY-MD", body={
                    'customerName': entry_merchant.name,
                }).retrieve_response('YYY-MD-RESULT').raw
            if credit_nl:
                merchant_info.update({
                    'list_type': credit_nl.get('listType'),
                    'list_reason': 'N/A' if not credit_nl.get('listReason') else credit_nl.get('listReason'),
                    'source': credit_nl.get('source'),
                })
            else:
                merchant_info.update({
                    'list_type': -1,
                    'list_reason': 'N/A',
                    'source': -1,
                })
        except:
            merchant_info.update({
                'list_type': -1,
                'list_reason': 'N/A',
                'source': -1,
            })

        result_body = super().merchant_entry(entry_code, factor_code, reception_picture, office_area_picture, 
                       merchant_info, legal_info, emergency_contact, attachment_info, practice_license_info, bill_info)

        if bill_info:
            if 'repay_day' in bill_info and bill_info.get('repay_day'):
                if bill_info.get('repay_day') < 1 or bill_info.get('repay_day') > 28:
                    raise UserError(_('还款日必须为1-28之间的整数！'))
                entry_merchant.write({
                    'repay_day': bill_info.get('repay_day'),
                    'credit_term': bill_info.get('credit_term', 1)
                })
            if 'requires_base' in bill_info and bill_info.get('requires_base'):
                entry_merchant.write({
                    'supplier_approval_base': bill_info.get('requires_base'),
                    'supplier_approval_multiple': bill_info.get('requires_multiple', 1)
                })

        return result_body

    @route(['/openapi/entry/merchant_approve'], type='json', auth="openapi", cors="*", methods=['POST', 'OPTIONS'], website=True)
    def merchant_approve(self, entry_code, approval, approval_info, reject_info):
        # 校验必填字段是否为空
        if not entry_code:
            raise UserError(_("请传入要审批的采购方进件编号！"))
        if (approval and (not approval_info or not approval_info.get('approval_opinion'))):
            raise UserError(_("审批通过时，请传入审批意见！"))
        if (not approval and (not reject_info or not reject_info.get('reject_opinion'))):
            raise UserError(_("审批拒绝时，请传入拒绝原因！"))

        # 查询对应进件记录同时判断是否可修改资料
        entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code', '=', entry_code)])
        if not entry_merchant.exists():
            raise UserError(_('根据传入的进件编号未找到对应的进件记录，请检查编号是否有误！'))
        if entry_merchant.state != 'approve':
            raise UserError(_('该进件记录在当前状态下不可进行审批操作！'))

        ap_entry_info = {
            'state': 'approval' if approval else 'rejected',
            'supplier_approval_time': fields.Datetime.now(),
        }
        # 审批通过
        if approval:
            if approval_info.get('approval_base'):
                ap_entry_info.update({
                    'supplier_approval_base': approval_info.get('approval_base'),
                    'supplier_approval_multiple': approval_info.get('approval_multiple', 1),
                    'supplier_final_quota': approval_info.get('approval_base') * approval_info.get('approval_multiple', 1),
                })
            if approval_info.get('repay_day'):
                if approval_info.get('repay_day') < 1 or approval_info.get('repay_day') > 28:
                    raise UserError(_('还款日必须为1-28之间的整数！'))
                ap_entry_info.update({
                    'repay_day': approval_info.get('repay_day'),
                    'credit_term': approval_info.get('credit_term', 1),
                })
            ap_entry_info.update({
                'supplier_approval_opinion': approval_info.get('approval_opinion'),
            })
        else:
            ap_entry_info.update({
                'reject_reason': reject_info.get('reject_opinion'),
                'reject_reason_simple': reject_info.get('reject_opinion'),
            })

        entry_merchant.write(ap_entry_info)

        if entry_merchant.state == 'rejected':
            message_body = {
                'approval_info': {
                    'entry_code': entry_merchant.seq_code,
                    'state': entry_merchant.state,
                    'hint': entry_merchant.reject_reason_simple,
                    'empty_list': [],
                    'account_info': None
                }
            }
            entry_merchant.message_handler(message_body)

        return {
            'entry_code': entry_merchant.seq_code,
            'state': entry_merchant.state,
            #'sign_url': entry_merchant.sign_url,
        }

    @route(['/openapi/merchant/approval'], type='http', cors="*", auth='public', methods=['GET'])
    def merchant_approval(self, mak, factor_code, token):
        if not mak:
            raise UserError(_('参数mak不能为空！'))
        if not factor_code:
            raise UserError(_('参数factor_code不能为空！'))
        if not token:
            raise UserError(_('参数token不能为空！'))
        
        # 供应方登录
        partner = request.env['res.partner'].sudo()._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
        partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})
        partner_user = partner.user_ids and partner.user_ids[0] or False
        request.update_env(user=partner_user.id)
        supplier = request.env['ifs.partner.supplier'].sudo().search([('root_employee_id.user_id', '=', partner_user.id)])
        if not supplier.exists():
            raise UserError(_('未找到相应的供应方，请检查传入的token是否有误或联系管理员！'))
        
        # 根据社会统一信用代码找到保理方
        factor = request.env['ifs.partner.factor'].search([('company_registry', '=', factor_code)])
        if not factor.exists():
            raise UserError(_('未找到对应的保理方信息，请检查社会统一信用代码填写是否有误！'))
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].search([('factor_id', '=', factor.id), ('supplier_id', '=', supplier.id)])
        if not factor_supplier.exists():
            raise UserError(_('当前保理方和供应方不存在关联关系，请重新上传！'))
        
        # 根据API_KEY找到唯一的采购进件记录
        api_app = request.env['galaxy.open.api.app'].sudo().search([('owner_id', '=', f'ifs.partner.supplier,{supplier.id}')], limit=1)
        if not api_app:
            raise UserError(_('没有找到对应的应用Owner！'))
        user_id = request.env["res.users.apikeys"].sudo()._check_credentials(
            'galaxy_token', api_app.app_id, scope='galaxy.open.api', key=mak)
        if not user_id:
            raise UserError(_('没有找到对应的采购方用户！'))
        user = request.env['res.users'].search([('id', '=', user_id)])
        entry_merchant = request.env['ifs.gar.entry.merchant'].search([('company_id', '=', user.company_id.id), ('supplier_id', '=', supplier.id), ('factor_id', '=', factor.id)], order='create_date desc', limit=1)
        if not entry_merchant:
            raise UserError(_('未查询到该采购方的进件信息，请确认上传信息是否有误！'))
        
        # 重定向到进件页面
        request.session.update({ 
            'pre_login': partner_user.login,
            'pre_uid': partner_user.id,
        })
        request.session.finalize(request.env)
        return request.redirect(f'/web#id={entry_merchant.id}&menu_id=217&active_id=13&model=ifs.gar.entry.merchant&view_type=form&hide_menu=1')