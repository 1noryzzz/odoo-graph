# -*- coding: utf-8 -*-

import base64
import json
import io
import fitz
import PyPDF2
from PyPDF2 import PdfFileReader
from PIL import Image
from functools import reduce
from operator import ge
from datetime import datetime
from odoo.exceptions import ValidationError, UserError

from odoo import http, _, fields
from odoo.http import request

from odoo.addons.portal.controllers import portal


class GuaranteeAccountsRecInvitePortal(portal.CustomerPortal):
    @http.route('/ifs_gar_invite/supplier/create', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def create_supplier_invite(self, **kw):
        if request.httprequest.method == 'POST':
            res_partner = request.env['res.partner'].search(
                [('parent_id', '=', False), ('phone', '=', kw.get('phone'))], limit=1)
            if not res_partner.exists():
                res_partner = request.env['res.partner'].create({
                    'name': kw.get('contact'),
                    'phone': kw.get('phone'),
                    'email': kw.get('email')
                })

            business = request.env['res.company.business.registration'].search(
                [('credit_no', '=', kw.get('credit_no'))])
            if request.env.company.ifs_partner == 'factor':
                factor = request.env['ifs.partner.factor'].search(
                    [('business_id.company_id', '=', request.env.company.id)])
            elif request.env.company.ifs_partner == 'franchisee':
                franchisee = request.env['ifs.partner.franchisee'].search(
                    [('business_id.company_id', '=', request.env.company.id)])
                factor = request.env['ifs.gar.partner.factor.franchisee'].search(
                    [('franchisee_id', '=', franchisee.id)]).factor_id
            sales = request.env['ifs.gar.sales'].sudo().search(
                [('partner_id', '=', request.env.user.partner_id.id)])

            invite_supplier = request.env['ifs.gar.invite.supplier'].create({
                'business_id': business.id,
                'factor_id': factor.id,
                'principal_id': res_partner.id,
                'phone': kw.get('phone'),
                'email': kw.get('email'),
                'sales_id': sales.id,
            })

            if kw.get('supplier_fee') == '月服务费+交易服务费':
                request.env['ifs.gar.partner.factor.supplier.fee'].create({
                    'according_to': 'monthly',
                    'fee': 25000,
                    'state': 'used',
                    'invite_id': invite_supplier.id,
                })
                request.env['ifs.gar.partner.factor.supplier.fee'].create({
                    'according_to': 'amount',
                    'rate': 0.6,
                    'state': 'used',
                    'invite_id': invite_supplier.id,
                })
            if kw.get('supplier_fee') == '阶梯收费':
                request.env['ifs.gar.partner.factor.supplier.fee'].create({
                    'according_to': 'amount',
                    'rate': 3,
                    'state': 'used',
                    'is_ladder': True,
                    'ladder_top': 0.0,
                    'invite_id': invite_supplier.id,
                })
                request.env['ifs.gar.partner.factor.supplier.fee'].create({
                    'according_to': 'amount',
                    'rate': 0.6,
                    'state': 'used',
                    'is_ladder': True,
                    'ladder_top': 400000,
                    'invite_id': invite_supplier.id,
                })
            # request.env['ifs.gar.partner.factor.supplier.fee'].create({
            #     'according_to': 'monthly',
            #     'for_setting_value': kw.get('supplier_fee'),
            #     'state': 'used',
            #     'invite_id': invite_supplier.id
            # })

            return request.render('ifs_gar_invite.ifs_gar_invite_supplier_succ_template', {
                'company_name': invite_supplier.business_id.name,
            })

            res_partner_model = request.env['res.partner']
            partner_name = kw.get('principal')
            partner_phone = kw.get('phone')
            partner_email = kw.get('email')
            partner = res_partner_model.search(
                [('name', '=', partner_name), ('phone', '=', partner_phone)])
            if not partner.exists():
                partner = res_partner_model.create({
                    'name': partner_name,
                    'phone': partner_phone,
                    'email': partner_email
                })

            request.env['ifs.gar.invite.merchant'].create({
                'company_name': kw.get('company_name'),
                'principal_id': partner.id,
                'phone': partner_phone,
                'email': partner_email,
                'website_id': request.website.id
            })

        return request.render('ifs_gar_invite.ifs_gar_invite_supplier_template', {})

    @http.route('/ifs_gar_invite/merchant/create', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def create_merchant_invite(self, **kw):
        if request.httprequest.method == 'POST':
            res_partner_model = request.env['res.partner']
            partner_name = kw.get('principal')
            partner_phone = kw.get('phone')
            partner_email = kw.get('email')
            partner = res_partner_model.search(
                [('name', '=', partner_name), ('phone', '=', partner_phone)])
            if not partner.exists():
                partner = res_partner_model.create({
                    'name': partner_name,
                    'phone': partner_phone,
                    'email': partner_email
                })

            request.env['ifs.gar.invite.merchant'].create({
                'company_name': kw.get('company_name'),
                'principal_id': partner.id,
                'phone': partner_phone,
                'email': partner_email,
                'website_id': request.website.id
            })

        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_template', {})

    @http.route('/ifs_gar_entry/franchisee/register/inform', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def to_franchisee_inform_page(self, **kw):
        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_inform_template', {})

    @http.route('/ifs_gar_entry/franchisee/register/business', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def register_business(self, **kw):
        # sales = request.env['ifs.gar.sales'].sudo().search(
        #     [('partner_id', '=', request.env.user.partner_id.id)])
        # if sales.exists():
        #     sales.sudo().write({
        #         'family_address': kw.get('family_address')
        #     })

        #     return request.render('ifs_gar_invite.ifs_gar_invite_franchisee_register_other_template', {})

        franchisee = request.env['ifs.gar.entry.franchisee'].search(
            [('company_id', '=', request.env.company.id)])
        if not franchisee.exists():
            invite_franchisee = request.env['ifs.gar.invite.franchisee'].search(
                [('company_id', '=', request.env.company.id)])
            invite_franchisee.sudo().start_entry()
            franchisee = invite_franchisee.entry_id

        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_register_business_template', {
            'ifs_company_id': franchisee.ifs_company_id,
            'company_info': {
                'establish_date': franchisee.raw.get('establish_date'),
                'address': franchisee.raw.get('address'),
            }
        })

    @http.route('/ifs_gar_entry/franchisee/register/business_license_ocr', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def business_license_ocr(self, business_license):
        Config = request.env['ir.config_parameter'].sudo()
        is_verification = Config.get_param(
            'ifs_base.verification_business_license', False)
        reg_ocr_api_code = Config.get_param(
            'ifs_base.business_reg_ocr_api_code', 'ALY-ALYSC-YYZZXXSB')
        franchisee = request.env['ifs.gar.entry.franchisee'].search(
            [('company_id', '=', request.env.company.id)])
        business_info = request.env['galaxy.external.api'].sudo().invoke(
            reg_ocr_api_code, body={'image': base64.encodebytes(business_license.read()).decode('utf8')}).retrieve_response('BUSINESS_INFO', False)
        if business_info and business_info.raw:
            if is_verification and business_info and (
                business_info.raw.get('name') != franchisee.name
                    or business_info.raw.get('reg_num') != franchisee.company_registry):
                raise UserError(_("营业执照识别信息与所填公司信息不一致，请检查营业执照是否清晰或联系管理员！"))
        else:
            raise UserError(_("营业执照识别失败，请检查营业执照是否清晰或联系管理员！"))

        return str(json.dumps({"success": _("营业执照信息验证成功")}, ensure_ascii=False))

    @http.route('/ifs_gar_entry/franchisee/register/basic', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def register_basic(self, business_license=False, **kw):
        # invite_sales = request.env['ifs.gar.invite.franchisee'].search(
        #     [('franchisee_partner_id', '=', request.env.user.partner_id.id)])
        # if invite_sales.exists():
        #     sales = request.env['ifs.gar.sales'].sudo().search(
        #         [('partner_id', '=', request.env.user.partner_id.id)])
        #     if not sales.exists():
        #         request.env['ifs.gar.sales'].sudo().with_context(quick_create=True).create({
        #             'partner_id': request.env.user.partner_id.id
        #         })

        #     return request.render(
        #         'ifs_gar_invite.ifs_gar_invite_franchisee_register_basic_template', {})

        if request.httprequest.method == 'POST':
            franchisee = request.env['ifs.gar.entry.franchisee'].search(
                [('company_id', '=', request.env.company.id)])
            if franchisee and business_license:
                franchisee.write({
                    'business_license': base64.encodebytes(business_license.read())
                })

            if franchisee and kw:
                bank_id = request.env['res.bank'].search(
                    [('name', '=', kw.get('deposit_bank'))]) if kw.get('deposit_bank') else False
                if not bank_id:
                    bank_id = request.env['res.bank'].create({
                        'name': kw.get('deposit_bank'),
                    })
                franchisee.write({
                    'bank_id': bank_id.id,
                    'acc_number': kw.get('account_no'),
                })

        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_register_basic_template', {})

    @http.route('/ifs_gar_entry/franchisee/register/retrieve_idcard_info', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def _retrieve_idcard_info(self, idcard_front_image, idcard_back_image):
        # invite_sales = request.env['ifs.gar.invite.franchisee'].search(
        #     [('franchisee_partner_id', '=', request.env.user.partner_id.id)])
        # if invite_sales.exists():
        #     current_partner = request.env.user.partner_id
        #     current_partner = request.env['ifs.gar.sales']._retrieve_idcard_info({
        #         'idcard_front_image': base64.encodebytes(idcard_front_image.read()),
        #         'idcard_back_image': base64.encodebytes(idcard_back_image.read()),
        #     }, current_partner)

        #     if not current_partner:
        #         return str(json.dumps({"errorMsg": "身份证信息不一致"}, ensure_ascii=False))

        #     sales = request.env['ifs.gar.sales'].sudo().search(
        #         [('partner_id', '=', current_partner.id)])
        #     idcard_info = json.dumps({
        #         'name': current_partner.name,
        #         'gender': '男' if current_partner.gender == 'male' else '女',
        #         'birthday': datetime.strftime(current_partner.idcard.birthday, '%Y-%m-%d'),
        #         'card_no': current_partner.idcard.card_no,
        #         'family_address': current_partner.idcard.address,
        #         'idcard_expiry_date': sales.idcard_expiry_date,
        #         'authority': current_partner.idcard.authority,
        #     }, ensure_ascii=False)
        # else:
        franchisee = request.env['ifs.gar.entry.franchisee'].search(
            [('company_id', '=', request.env.company.id)])

        try:
            idcard_front_image = base64.encodebytes(idcard_front_image.read())
            idcard_back_image = base64.encodebytes(idcard_back_image.read())
            franchisee.sudo()._retrieve_idcard_info(idcard_front_image, idcard_back_image)
        except (ValidationError, UserError) as e:
            return str(json.dumps({"errorMsg": e.name}, ensure_ascii=False))
        except:
            request.env.cr.rollback()
            return str(json.dumps({"errorMsg": "身份证号已存在！"}, ensure_ascii=False))
        
        
        idcard_expiry_date = _('至').join([franchisee.legal_start_date, franchisee.legal_end_date if franchisee.legal_end_date else _(' 长期')])
        idcard_info = json.dumps({
            'name': franchisee.legal_name,
            'gender': '男' if franchisee.legal_gender == 'male' else '女',
            'birthday': franchisee.legal_birthday,
            'card_no': franchisee.legal_id_number,
            'family_address': franchisee.legal_address,
            'idcard_expiry_date': idcard_expiry_date,
            'authority': franchisee.legal_authority,
        }, ensure_ascii=False)

        return str(idcard_info)

    @http.route('/ifs_gar_entry/franchisee/register/other', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def register_other(self, **kw):
        if kw:
            franchisee = request.env['ifs.gar.entry.franchisee'].search(
                [('company_id', '=', request.env.company.id)])
            franchisee.write({
                'legal_address': kw.get('family_address')
            })

        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_register_other_template', {})

    @http.route('/ifs_gar_entry/franchisee/register/sign', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def register_sign(self, **kw):
        # sales = request.env['ifs.gar.sales'].sudo().search(
        #     [('partner_id', '=', request.env.user.partner_id.id)])
        # if sales.exists():
        #     franchisee = sales
        #     sign_party = request.env.user
        #     sign_party_model = 'res.users'
        #     invite_franchisee = request.env['ifs.gar.invite.franchisee'].sudo().search(
        #         [('franchisee_partner_id', '=', request.env.user.partner_id.id)])
        # else:

        franchisee = request.env['ifs.gar.entry.franchisee'].sudo().search(
            [('company_id', '=', request.env.company.id)])
        if franchisee.invite_id.ifs_company_id.org_auth_state != 'certified':
            franchisee.invite_id.ifs_company_id.sudo().certificate_company()
        invite_franchisee = franchisee.invite_id
        if not franchisee.f42_contract_info_id:
            f42_contract_template = request.env['ifs.contract.template'].sudo().search([
                ('code', '=', 'F42')])
            kw['f42_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                'name': f42_contract_template.name,
                'partner_one': '%s,%d' % (franchisee._name, franchisee.id),
                'template_id': f42_contract_template.id,
            })
        if not franchisee.f43_contract_info_id:
            f43_contract_template = request.env['ifs.contract.template'].sudo().search([
                ('code', '=', 'F43')])
            kw['f43_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                'name': f43_contract_template.name,
                'partner_one': '%s,%d' % (franchisee._name, franchisee.id),
                'template_id': f43_contract_template.id,
            })
        factor = invite_franchisee.factor_id
        if not franchisee.p01_contract_info_id:
            p01_contract_template = request.env['ifs.contract.template'].sudo().retrieve_by_code('P01', factor.id)

            kw['p01_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                'name': p01_contract_template.name,
                'partner_one': '%s,%d' % ('ifs.partner.factor', factor.id),
                'partner_two': '%s,%d' % (franchisee._name, franchisee.id),
                'template_id': p01_contract_template.id,
                'partner_two_signature': factor.signature,
                'params': json.dumps({
                    'franchisee_type_value': '11111',
                    'franchisee_type': '1111',
                    'province': str('广东省').replace('省', '').replace('市', ''),
                    'city': str('深圳市').replace('市', ''),
                    'area_agency_fee': '11111',
                    'first_year_base_service_fee': '11111%',
                    'first_year_trade_service_fee': '11111%',
                    'follow_up_base_service_fee': '11111%',
                    'follow_up_trade_service_fee': '11111%',
                })
            })
        # franchisee.write(kw)

        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_register_sign_template', {
            'contract_infos': [franchisee.f42_contract_info_id,
                               franchisee.f43_contract_info_id,
                               franchisee.p01_contract_info_id]
        })

    @http.route('/ifs_gar_entry/franchisee/register/to_sign_page', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def to_sign_page(self, **kw):
        return request.render('ifs_gar_entry.franchisee_sign', {})

    @http.route('/ifs_gar_entry/franchisee/register/signature', type='json', auth="user", website=True)
    def contract_signature(self, signature=None):
        if not signature:
            return {'error': _('未收到签名信息')}

        im = Image.open(io.BytesIO(base64.b64decode(signature)))
        if im.width < im.height:
            im = im.rotate(90, expand=True)
            b = io.BytesIO()
            im.save(b, format="PNG")
            signature = base64.b64encode(b.getvalue())

        # sales = request.env['ifs.gar.sales'].sudo().search(
        #     [('partner_id', '=', request.env.user.partner_id.id)])
        # invite_user = {}
        # if sales.exists():
        #     invite_user = sales
        # else:
        franchisee = request.env['ifs.gar.entry.franchisee'].search(
            [('company_id', '=', request.env.company.id)])

        franchisee.p01_contract_info_id.sudo().write({
            'partner_two_signature': signature,
            'state': 'confirmed'
        })
        franchisee.f42_contract_info_id.sudo().write({
            'partner_one_signature': signature,
            'state': 'signed'
        })
        franchisee.f43_contract_info_id.sudo().write({
            'partner_one_signature': signature,
            'state': 'signed'
        })
        franchisee.p01_contract_info_id.sudo().signature_all()
        franchisee.f42_contract_info_id.sudo().signature_all()
        franchisee.f43_contract_info_id.sudo().signature_all()

        # invite_user.sudo().active_franchisee()
        franchisee.state = 'committed'

        return {
            'force_refresh': True,
            'redirect_url': '/ifs_gar_entry/franchisee/register/finish'
        }

    @http.route('/ifs_gar_entry/franchisee/register/finish', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def register_finish(self, **kw):
        return request.render('ifs_gar_entry.ifs_gar_entry_franchisee_register_finish_template', {})

    @http.route('/ifs_gar_entry/franchisee/register/steps', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def _register_steps(self):
        # invite_sales = request.env['ifs.gar.invite.franchisee'].search(
        #     [('franchisee_partner_id', '=', request.env.user.partner_id.id)])
        # entry_steps = []
        # if invite_sales.exists():
        #     entry_steps = request.env['ifs.gar.sales'].get_entry_steps()
        # else:
        entry_steps = request.env['ifs.partner.franchisee'].get_entry_steps(
        )

        return str(entry_steps)

    @http.route('/ifs_gar_invite/merchant/register/inform', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_to_franchisee_inform_page(self, **kw):
        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_inform_template', {})

    @http.route('/ifs_gar_invite/merchant/register/basic', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_register_basic(self, business_license=False, **kw):

        if request.httprequest.method == 'POST':
            if business_license:
                business = request.env['res.company.business.registration'].search(
                    [('company_id', '=', request.env.company.id)])
                business.write({
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

        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_basic_template', {})

    @http.route('/ifs_gar_invite/merchant/register/business', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_register_business(self, **kw):

        merchant = request.env['ifs.partner.merchant'].search(
            [('business_id.company_id', '=', request.env.company.id)])
        if not merchant.exists():
            invite_merchant = request.env['ifs.gar.invite.merchant'].search(
                [('business_id.company_id', '=', request.env.company.id)])
            invite_merchant.start_entry_portal()
            merchant = invite_merchant.merchant_id

        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_business_template', {
            'business': merchant.business_id,
        })

    @http.route('/ifs_gar_invite/merchant/register/docs', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_register_docs(self, **kw):
        if kw:
            merchant = request.env['ifs.partner.merchant'].search(
                [('business_id.company_id', '=', request.env.company.id)])
            merchant.write({
                'family_address': kw.get('family_address')
            })
            merchant.certificate_company()

        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_docs_template', {})

    # @http.route('/ifs_gar_invite/merchant/register/other', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    # def merchant_register_other(self, **kw):
    #     doorhead_picture = kw.get('doorhead_picture')
    #     indoor_picture = kw.get('indoor_picture')
    #     selfie_picture = kw.get('selfie_picture')
    #     merchant = request.env['ifs.partner.merchant'].sudo().search(
    #         [('business_id.company_id', '=', request.env.company.id)])
    #     data={}
    #     if doorhead_picture:
    #         data['doorhead_picture']=base64.encodebytes(doorhead_picture.read())
    #     if indoor_picture:
    #         data['indoor_picture']=base64.encodebytes(indoor_picture.read())
    #     if selfie_picture:
    #         data['selfie_picture']=base64.encodebytes(selfie_picture.read())
    #     merchant.write(data)
    #     if request.httprequest.method == 'POST':
    #         return self.merchant_register_sign()
        # return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_other_template', {})

    @http.route('/ifs_gar_invite/merchant/register/sign', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_register_sign(self, **kw):
        merchant = request.env['ifs.partner.merchant'].sudo().search(
            [('business_id.company_id', '=', request.env.company.id)])
        if request.httprequest.method == 'POST':
            doorhead_picture = kw.get('doorhead_picture')
            indoor_picture = kw.get('indoor_picture')
            selfie_picture = kw.get('selfie_picture')

            data = {}
            if doorhead_picture:
                data['doorhead_picture'] = base64.encodebytes(
                    doorhead_picture.read())
            if indoor_picture:
                data['indoor_picture'] = base64.encodebytes(
                    indoor_picture.read())
            if selfie_picture:
                data['selfie_picture'] = base64.encodebytes(
                    selfie_picture.read())
            merchant.write(data)
        if merchant.doorhead_picture and merchant.indoor_picture and merchant.selfie_picture:
            contract_ids = {}
            if not merchant.f41_contract_info_id.exists():
                f41_template = request.env['ifs.contract.template'].sudo().search([
                    ('code', '=', 'F41')])
                contract_ids['f41_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                    'name': f41_template.name,
                    'partner_one': '%s,%d' % (merchant._name, merchant.id),
                    'template_id': f41_template.id,
                }).id
            if not merchant.f42_contract_info_id.exists():
                f42_template = request.env['ifs.contract.template'].sudo().search([
                    ('code', '=', 'F42')])
                contract_ids['f42_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                    'name': f42_template.name,
                    'partner_one': '%s,%d' % (merchant._name, merchant.id),
                    'template_id': f42_template.id,
                }).id
            if not merchant.f43_contract_info_id.exists():
                f43_template = request.env['ifs.contract.template'].sudo().search([
                    ('code', '=', 'F43')])
                contract_ids['f43_contract_info_id'] = request.env['ifs.contract.info'].sudo().create({
                    'name': f43_template.name,
                    'partner_one': '%s,%d' % (merchant._name, merchant.id),
                    'template_id': f43_template.id,
                }).id

            merchant.write(contract_ids)

            return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_sign_template', {
                'contract_infos': {merchant.f42_contract_info_id,
                                   merchant.f43_contract_info_id,
                                   merchant.f41_contract_info_id, }
            })

    @http.route('/ifs_gar_invite/merchant/register/finish', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def merchant_register_finish(self, **kw):
        return request.render('ifs_gar_invite.ifs_gar_invite_merchant_register_finish_template', {})

    @http.route('/ifs_gar_invite/merchant/register/to_sign_page', type='http', methods=['GET', 'POST'], auth="public", website=True, csrf=False)
    def merchant_to_sign_page(self, **kw):
        return request.render('ifs_gar_invite.merchant_sign', {})

    @http.route('/ifs_gar_invite/merchant/register/signature', type='json', auth="user", website=True)
    def merchant_contract_signature(self, signature=None):
        if not signature:
            return {'error': _('未收到签名信息')}

        im = Image.open(io.BytesIO(base64.b64decode(signature)))
        if im.width < im.height:
            im = im.rotate(90, expand=True)
            b = io.BytesIO()
            im.save(b, format="PNG")
            signature = base64.b64encode(b.getvalue())

        # sales = request.env['ifs.gar.sales'].sudo().search(
        #     [('partner_id', '=', request.env.user.partner_id.id)])
        # invite_user = {}
        # if sales.exists():
        #     invite_user = sales
        # else:
        invite = request.env['ifs.gar.invite.merchant'].sudo().search(
            [('business_id.company_id', '=', request.env.company.id)])
        invite_user = request.env['ifs.partner.merchant'].search(
            [('business_id.company_id', '=', request.env.company.id)])

        invite_user.f41_contract_info_id.sudo().write({
            'partner_one_signature': signature,
            'state': 'signed'
        })
        invite_user.f42_contract_info_id.sudo().write({
            'partner_one_signature': signature,
            'state': 'signed'
        })
        invite_user.f43_contract_info_id.sudo().write({
            'partner_one_signature': signature,
            'state': 'signed'
        })
        invite_user.f41_contract_info_id.sudo().signature_all()
        invite_user.f42_contract_info_id.sudo().signature_all()
        invite_user.f43_contract_info_id.sudo().signature_all()

        # invite_user.sudo().active_merchant()
        invite.state = 'auditing'

        return {
            'force_refresh': True,
            'redirect_url': '/ifs_gar_invite/merchant/register/finish'
        }

    @http.route('/ifs_gar_invite/merchant/register/retrieve_idcard_info', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_retrieve_idcard_info(self, idcard_front_image, idcard_back_image):

        merchant = request.env['ifs.partner.merchant'].search(
            [('business_id.company_id', '=', request.env.company.id)])

        try:
            current_partner = merchant._retrieve_idcard_info({
                'idcard_front_image': base64.encodebytes(idcard_front_image.read()),
                'idcard_back_image': base64.encodebytes(idcard_back_image.read()),
            })
        except (ValidationError, UserError) as e:
            return str(json.dumps({"errorMsg": e.name}, ensure_ascii=False))
        except:
            request.env.cr.rollback()
            return str(json.dumps({"errorMsg": "身份证号已存在！"}, ensure_ascii=False))

        if not current_partner:
            return str(json.dumps({"errorMsg": "身份证信息不一致"}, ensure_ascii=False))

        idcard_info = json.dumps({
            'name': merchant.principal_id.name,
            'gender': '男' if merchant.principal_id.gender == 'male' else '女',
            'birthday': datetime.strftime(merchant.idcard.birthday, '%Y-%m-%d'),
            'card_no': merchant.idcard.card_no,
            'family_address': merchant.idcard.address,
            'idcard_expiry_date': merchant.idcard_expiry_date,
            'authority': merchant.idcard.authority,
        }, ensure_ascii=False)

        return str(idcard_info)

    @http.route('/ifs_gar_invite/merchant/register/steps', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_register_steps(self):
        # invite_sales = request.env['ifs.gar.invite.franchisee'].search(
        #     [('franchisee_partner_id', '=', request.env.user.partner_id.id)])
        # entry_steps = []
        # if invite_sales.exists():
        #     entry_steps = request.env['ifs.gar.sales'].get_entry_steps()
        # else:
        entry_steps = request.env['ifs.partner.merchant'].get_entry_steps(
        )

        return str(entry_steps)

    @http.route('/ifs_gar_invite/merchant/register/business_license_ocr', type='http', methods=['GET', 'POST'], auth="user", website=True, csrf=False)
    def merchant_business_license_ocr(self, business_license):
        try:
            resp = request.env['ifs.base.company.mixin'].business_license_ocr(
                base64.encodebytes(business_license.read()))
        except (ValidationError, UserError) as error:
            return str(json.dumps({"errorMsg": error.name}, ensure_ascii=False))
        except:
            request.env.cr.rollback()
            return str(json.dumps({"errorMsg": _("系统繁忙,请稍后再试或直接联系管理员")}, ensure_ascii=False))

        business = request.env['res.company.business.registration'].search(
            [('company_id', '=', request.env.company.id)])
        # if resp.get('reg_num') != business.credit_no:
        #     return str(json.dumps({"errorMsg": _("营业执照信息不一致")}, ensure_ascii=False))

        return str(json.dumps({"success": _("营业执照信息验证成功")}, ensure_ascii=False))
    
    #刷新PDF文件预览图
    @http.route('/ifs_gar_entry/refresh_pdf_preview', type='http', methods=['GET'], auth="user", website=True)
    def refresh_pdf_preview(self, **kw):
        entry_merchants = request.env['ifs.gar.entry.merchant'].sudo().search([])
        # entry_merchants = request.env['ifs.gar.entry.merchant'].sudo().browse([3])
        for entry_merchant in entry_merchants:
            try:
                if entry_merchant.legal_person_property_certificate and not entry_merchant.legal_person_property_certificate_preview:
                    entry_merchant.legal_person_property_certificate_preview = self._intercept_preview(entry_merchant.legal_person_property_certificate)
                if entry_merchant.charter and not entry_merchant.charter_preview:
                    entry_merchant.charter_preview = self._intercept_preview(entry_merchant.charter)
                if entry_merchant.lease_contract and not entry_merchant.lease_contract_preview:
                    entry_merchant.lease_contract_preview = self._intercept_preview(entry_merchant.lease_contract)
                if entry_merchant.half_year_balance_sheet and not entry_merchant.half_year_balance_sheet_preview:
                    entry_merchant.half_year_balance_sheet_preview = self._intercept_preview(entry_merchant.half_year_balance_sheet)
                if entry_merchant.half_year_cash_flow_sheet and not entry_merchant.half_year_cash_flow_sheet_preview:
                    entry_merchant.half_year_cash_flow_sheet_preview = self._intercept_preview(entry_merchant.half_year_cash_flow_sheet)
                if entry_merchant.half_year_assets_gains_losses_sheet and not entry_merchant.half_year_assets_gains_losses_sheet_preview:
                    entry_merchant.half_year_assets_gains_losses_sheet_preview = self._intercept_preview(entry_merchant.half_year_assets_gains_losses_sheet)
                if entry_merchant.enterprise_property_certificate and not entry_merchant.enterprise_property_certificate_preview:
                    entry_merchant.enterprise_property_certificate_preview = self._intercept_preview(entry_merchant.enterprise_property_certificate)
            except PyPDF2.utils.PdfReadError:
                continue
            
        return _('合同预览刷新成功！')
    
    def _intercept_preview(self, data):
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