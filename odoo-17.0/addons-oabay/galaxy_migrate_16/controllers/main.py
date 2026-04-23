# -*- coding: utf-8 -*-

import json,datetime
import odoo.http as http
from _ctypes import  PyObj_FromPtr
import base64
from odoo.http import request
from odoo.tools.misc import get_lang
from ..tools import rpc,migrate_data17
from odoo import _, api, fields, models

class GalaxyMigrate(http.Controller):
    
 
    @http.route('/picker5', type='http', auth="user", website=True)
    def picker5(self, **kwargs):
       
        return request.render('galaxy_migrate_16.galaxy_picker5', {})
    
    @http.route('/getstate', type='json', auth='public')
    def getstate(self, **kwargs):
        country = request.env['res.country'].sudo().search([('name','=','中国')])
        state_list = request.env['res.country.state'].sudo().search([('country_id','=',country.id)])
        province = []
        for state in state_list:
            province.append({
                "text":state.name,"value":state.id
                })
        return province
    @http.route('/getcity', type='json', auth='public')
    def getcity(self, **kwargs):
        id = kwargs.get("id")
        area_list = request.env['res.country.area'].sudo().search([('state_id','=',int(id)),('area_type','in',['city','dc'])])
        
        city = []
        for area in area_list:
            city.append({
                "text":area.name,"value":area.id
                })
        return city
    
    @http.route('/getarea', type='json', auth='public')
    def getarea(self, **kwargs):
        id = kwargs.get("id")
        area_list = request.env['res.country.area'].sudo().search([('parent_area_id','=',int(id)),('area_type','=','area')])
        
        areas = []
        for area in area_list:
            areas.append({
                "text":area.name,"value":area.id
                })
        return areas
    

    @http.route('/migrate', type='http', auth="user")
    def migrate(self, **kwargs):
        obj={
            "res.partner":{},
            "res.company":{},
            "res.company.business.registration":{},
            "wechat.offiaccount.config":{},
            "res.partner.idcard":{},
            "res.users":{},
            "website":{},
        }
        factor_list = self.get_factor_list(obj)

        return request.make_json_response(factor_list)
    
    @http.route('/migrate_contract', type='http', auth="user")
    def migrate_contract(self, **kwargs):
        self.migrate_merchant_contract()
        return request.make_json_response({})
    def migrate_supplier_contract(self):
        invite_suppliers = request.env['ifs.gar.invite.supplier'].sudo().search([])

        for invite_supplier in invite_suppliers:
            if invite_supplier.state == 'ready':
                invite_supplier.supplier_id.active_supplier()
                
            if invite_supplier.supplier_id.exists():
                factor_supplier_id = request.env['ifs.gar.partner.factor.supplier'].sudo().search(
                    [('factor_id', '=', invite_supplier.factor_id.id), ('supplier_id', '=', invite_supplier.supplier_id.id)])
                if not factor_supplier_id.exists():
                    factor_supplier = rpc.do_rpc({}, 'search_read', {
                        "model": "ifs.gar.partner.factor.supplier",
                        "fields": ["currency_id","total_quota","other_fee_remark"],
                        "domain": [("factor_id.business_id.credit_no","=",invite_supplier.factor_id.business_id.credit_no),
                                ("supplier_id.business_id.credit_no","=",invite_supplier.supplier_id.business_id.credit_no)],
                    }).get("records")[0]
                    factor_supplier_id = request.env['ifs.gar.partner.factor.supplier'].sudo().create({
                        'factor_id':invite_supplier.factor_id.id,
                        'supplier_id':invite_supplier.supplier_id.id,
                        'currency_id':factor_supplier['currency_id'][0],
                        'total_quota':factor_supplier['total_quota'],
                        'other_fee_remark':factor_supplier['other_fee_remark']
                    })
            else:
                factor_supplier_id=False
            old_invite_supplier = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.gar.invite.supplier",
                "fields": ["name", "phone", "email", "business_id", "code", "cut_off_time", "id", "other_fee_remark", "sales_id", "state", "supplier_id"],
                "domain": [('credit_no', '=', invite_supplier.credit_no)],
            }).get("records")[0]
            factor_supplier_fees = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.gar.partner.factor.supplier.fee",
                "fields": ["invite_id", "state", "according_to", "rate", "fee", "is_ladder", "ladder_top", "for_setting_value", "sequence"],
                "domain": [("invite_id", "=", old_invite_supplier['id'])],
            }).get("records")
            for factor_supplier_fee in factor_supplier_fees:
                factor_supplier_fee_id = request.env['ifs.gar.partner.factor.supplier.fee'].sudo().search(
                    [('invite_id', '=', invite_supplier.id), ('rate', '=', factor_supplier_fee['rate'])])
                if not factor_supplier_fee_id.exists():
                    fee={
                        'invite_id': invite_supplier.id,
                        'state': factor_supplier_fee['state'],
                        'according_to': factor_supplier_fee['according_to'],
                        'rate': factor_supplier_fee['rate'],
                        'fee': factor_supplier_fee['fee'],
                        'is_ladder': factor_supplier_fee['is_ladder'],
                        'ladder_top': factor_supplier_fee['ladder_top'],
                        'for_setting_value': factor_supplier_fee['for_setting_value'],
                        'sequence': factor_supplier_fee['sequence'],
                    }
                    if factor_supplier_id:
                        fee['factor_supplier_id']=factor_supplier_id.id
                    request.env['ifs.gar.partner.factor.supplier.fee'].create(fee)
            if invite_supplier.supplier_id.exists() and invite_supplier.supplier_id.current_entry_step == 'finish':
                t17_template = request.env['ifs.contract.template'].sudo().search([('code', '=', 'T17')])
                t21_template = request.env['ifs.contract.template'].sudo().search([('code', '=', 'T21')])
                f42_template = request.env['ifs.contract.template'].sudo().search([('code', '=', 'F42')])
                f43_template = request.env['ifs.contract.template'].sudo().search([('code', '=', 'F43')])
                supplier = rpc.do_rpc({}, 'search_read', {
                    "model": "ifs.partner.supplier",
                    "fields": ["id","name","t17_contract_info_id","t21_contract_info_id","f42_contract_info_id","f43_contract_info_id"],
                    "domain": [("business_id.credit_no","=",invite_supplier.business_id.credit_no)],
                }).get("records")[0]
                t17_contract_info=self.get_record(supplier['t17_contract_info_id'][0],'ifs.contract.info',{})
                t21_contract_info=self.get_record(supplier['t21_contract_info_id'][0],'ifs.contract.info',{})
                f42_contract_info=self.get_record(supplier['f42_contract_info_id'][0],'ifs.contract.info',{})
                f43_contract_info=self.get_record(supplier['f43_contract_info_id'][0],'ifs.contract.info',{})
                t17_contract_info['partner_one']='{},{}'.format('ifs.partner.supplier',invite_supplier.supplier_id.id)
                t17_contract_info['partner_two']='{},{}'.format('ifs.partner.factor',invite_supplier.factor_id.id)
                t17_contract_info['template_id']=t17_template.id
                
                t21_contract_info['partner_one']='{},{}'.format('ifs.partner.supplier',invite_supplier.supplier_id.id)
                t21_contract_info['partner_two']='{},{}'.format('ifs.partner.factor',invite_supplier.factor_id.id)
                t21_contract_info['template_id']=t21_template.id
                
                f42_contract_info['partner_one']='{},{}'.format('ifs.partner.supplier',invite_supplier.supplier_id.id)
                f42_contract_info['template_id']=f42_template.id
                f43_contract_info['partner_one']='{},{}'.format('ifs.partner.supplier',invite_supplier.supplier_id.id)
                f43_contract_info['template_id']=f43_template.id
                invite_supplier.supplier_id.sudo().write({
                    't17_contract_info_id':request.env['ifs.contract.info'].create(t17_contract_info).id,
                    't21_contract_info_id':request.env['ifs.contract.info'].create(t21_contract_info).id,
                    'f42_contract_info_id':request.env['ifs.contract.info'].create(f42_contract_info).id,
                    'f43_contract_info_id':request.env['ifs.contract.info'].create(f43_contract_info).id
                })
            
    @http.route('/migrate_merchant_contract', type='http', auth="user")
    def migrate_merchant_contract(self):
        
        f41_template = request.env['ifs.contract.template'].search([('code', '=', 'F41')])
        f42_template = request.env['ifs.contract.template'].search([('code', '=', 'F42')])
        f43_template = request.env['ifs.contract.template'].search([('code', '=', 'F43')])
        t18_template = request.env['ifs.contract.template'].search([('code', '=', 'T18')])
        t19_template = request.env['ifs.contract.template'].search([('code', '=', 'T19')])
        t20_template = request.env['ifs.contract.template'].search([('code', '=', 'T20')])
        merchant_ids = request.env['ifs.partner.merchant'].sudo().search([])
        for merchant_id in merchant_ids:    
            invite_id = request.env['ifs.gar.invite.merchant'].sudo().search([('merchant_id','=',merchant_id.id)])
            # sub_loan_account = request.env['ifs.gar.sub.loan.account'].sudo().search([
            #     ('supplier_id', '=', merchant_id.invite_id.supplier_id.id),
            #     ('merchant_id', '=', merchant_id.id)
            # ])
            merchant = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.partner.merchant",
                "fields": ['id','f41_contract_info_id','f42_contract_info_id','f43_contract_info_id','t18_contract_info_id','f41_guarantor_contract_info_id','f42_guarantor_contract_info_id','f43_guarantor_contract_info_id'],
                "domain": [("business_id.credit_no","=",merchant_id.business_id.credit_no)],
            }).get("records")[0]
            if merchant_id.current_entry_step == 'pending' or merchant_id.current_entry_step == 'activation':
                f41_contract_info=self.get_record(merchant['f41_contract_info_id'][0],'ifs.contract.info',{})
                f42_contract_info=self.get_record(merchant['f42_contract_info_id'][0],'ifs.contract.info',{})
                f43_contract_info=self.get_record(merchant['f43_contract_info_id'][0],'ifs.contract.info',{})
                
                f41_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                f42_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                f43_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                f41_contract_info['template_id']=f41_template.id
                f42_contract_info['template_id']=f42_template.id
                f43_contract_info['template_id']=f43_template.id
                merchant_id.write({
                    'f41_contract_info_id':request.env['ifs.contract.info'].sudo().create(f41_contract_info).id,
                    'f42_contract_info_id':request.env['ifs.contract.info'].sudo().create(f42_contract_info).id,
                    'f43_contract_info_id':request.env['ifs.contract.info'].sudo().create(f43_contract_info).id
                })
                if merchant['t18_contract_info_id']:
                    t18_contract_info=self.get_record(merchant['t18_contract_info_id'][0],'ifs.contract.info',{})
                    t18_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                    t18_contract_info['partner_two']='%s,%d' % ('ifs.partner.factor', merchant_id.invite_id.factor_id.id)

                    t18_contract_info['template_id']=t18_template.id
                    merchant_id.write({
                        't18_contract_info_id':request.env['ifs.contract.info'].sudo().create(t18_contract_info).id,
                    })
                
                if merchant_id.is_legal_person:
                    merchant_id.f41_guarantor_contract_info_id = merchant_id.f41_contract_info_id
                    merchant_id.f42_guarantor_contract_info_id = merchant_id.f42_contract_info_id
                    merchant_id.f43_guarantor_contract_info_id = merchant_id.f43_contract_info_id
                elif merchant['f41_guarantor_contract_info_id']:
                    f41_guarantor_contract_info=self.get_record(merchant['f41_guarantor_contract_info_id'][0],'ifs.contract.info',{})
                    f42_guarantor_contract_info=self.get_record(merchant['f42_guarantor_contract_info_id'][0],'ifs.contract.info',{})
                    f43_guarantor_contract_info=self.get_record(merchant['f43_guarantor_contract_info_id'][0],'ifs.contract.info',{})
                    f41_guarantor_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                    f42_guarantor_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                    f43_guarantor_contract_info['partner_one']='{},{}'.format('ifs.partner.merchant',merchant_id.id)
                    f41_guarantor_contract_info['template_id']=f41_template.id
                    f42_guarantor_contract_info['template_id']=f42_template.id
                    f43_guarantor_contract_info['template_id']=f43_template.id
                    merchant_id.write({
                        'f41_guarantor_contract_info_id':request.env['ifs.contract.info'].sudo().create(f41_guarantor_contract_info).id,
                        'f42_guarantor_contract_info_id':request.env['ifs.contract.info'].sudo().create(f42_guarantor_contract_info).id,
                        'f43_guarantor_contract_info_id':request.env['ifs.contract.info'].sudo().create(f43_guarantor_contract_info).id
                    })
            if merchant_id.state == 'normal':
                merchant_id.active_merchant()
                trade_order_columns = ["supplier_id","transaction_fee_rate","item_ids","sub_loan_account_id","image_1920","state","code","order_code","trade_amount","merchant_id","bill_id","bill_log_id","trade_date","repayment_date","currency_id","remark","merchant_president","merchant_chairman","delivery","withdrawal_amount","accounting_period","id","display_name","create_date","write_date","t19_contract_info_id","t20_contract_info_id"]
                trade_orders = rpc.do_rpc({}, 'search_read', {
                    "model": "ifs.gar.trade.order",
                    "fields": trade_order_columns,
                    "domain": [("merchant_id.business_id.credit_no","=",merchant_id.business_id.credit_no)],
                }).get("records")
                current_bill_order=[]
                for trade_order in trade_orders:
                    trade_order_id  = request.env['ifs.gar.trade.order'].sudo().search([('code','=',trade_order['code'])])
                    if trade_order_id.exists():
                        continue
                    supplier_id=request.env['ifs.partner.supplier'].sudo().search([('business_id.company_id.name','=',trade_order['supplier_id'][1])])

                    sub_loan_account_id = request.env['ifs.gar.sub.loan.account'].sudo().search([('supplier_merchant_id.merchant_id','=',merchant_id.id),('supplier_merchant_id.supplier_id','=',invite_id.supplier_id.id)])
                    
                    trade_order['currency_id']=trade_order['currency_id'][0]
                    trade_order['merchant_id']=merchant_id.id
                    trade_order['supplier_id']=supplier_id.id
                    trade_order['sub_loan_account_id']=sub_loan_account_id.id
                    trade_order.pop('item_ids')
                    bill = self.get_record(trade_order['bill_id'][0],'ifs.gar.loan.account.bill',{})
                    trade_order.pop('bill_id')
                    trade_order.pop('bill_log_id')
                    repayment_date = datetime.datetime.strptime(trade_order['repayment_date'],"%Y-%m-%d %H:%M:%S")-datetime.timedelta(days=1)
                    trade_order['repayment_date']=repayment_date
                    t19_contract_info=self.get_record(trade_order['t19_contract_info_id'][0],'ifs.contract.info',{})
                    t20_contract_info=self.get_record(trade_order['t20_contract_info_id'][0],'ifs.contract.info',{})
                    t19_contract_info['partner_one']="{},{}".format('ifs.partner.factor', sub_loan_account_id.loan_account_id.factor_id.id)
                    t19_contract_info['partner_two']='{},{}'.format('ifs.partner.supplier', supplier_id.id)
                    t19_contract_info['partner_three']='{},{}'.format('ifs.partner.merchant', merchant_id.id)
                    t19_contract_info['template_id']=t19_template.id
                    t20_contract_info['partner_one']='{},{}'.format('ifs.partner.factor', sub_loan_account_id.loan_account_id.factor_id.id)
                    t20_contract_info['partner_two']='{},{}'.format('ifs.partner.merchant', merchant_id.id)
                    t20_contract_info['partner_three']='{},{}'.format('ifs.partner.supplier', supplier_id.id)
                    t20_contract_info['template_id']=t20_template.id
                    trade_order.pop('t19_contract_info_id')
                    trade_order.pop('t20_contract_info_id')

                    trade_order_id = request.env['ifs.gar.trade.order'].sudo().create(trade_order)
                    if trade_order_id.state == 'confirmed':
                        trade_order_id.state='draft'
                        trade_order_id.action_commit_order()
                        trade_order_id.action_confirm_order()
                        trade_order_id.after_sign('signed')
                        trade_order_id.after_sign('signed')
                        if bill['state']=='current':
                            trade_order_id.bill_id.state='paid'
                            current_bill_order.append(trade_order_id)
                        else:
                            trade_order_id.bill_id.state=bill['state']
                        trade_order_id.write({
                            't19_contract_info_id':request.env['ifs.contract.info'].sudo().create(t19_contract_info).id,
                            't20_contract_info_id':request.env['ifs.contract.info'].sudo().create(t20_contract_info).id
                        })
                for order in  current_bill_order:
                    order.bill_id.state='current'

                                           
                    
    def migrate_franchisee_contract(self):
        franchisee_columns=["business_address","business_id", "contact_partner_id", "credit_no", "financial_manager_id","industry","industry_selection","industry_time","industry_resources",
                       "id", "org_auth_state", "state","business_license","deposit_license","account_ids","franchisee_suggest","family_address","current_entry_step",
                       "f42_contract_info_id","f43_contract_info_id","p01_contract_info_id"]
        franchisees = request.env['ifs.partner.franchisee'].search([('state','=','normal')])
        
        for franchisee in franchisees:
            old_franchisee = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.partner.franchisee",
                "fields": franchisee_columns,
                "domain": [("business_id.credit_no","=",franchisee.business_id.credit_no)],
            }).get("records")[0]
            factor=request.env['ifs.gar.invite.franchisee'].search([('franchisee_id','=',franchisee.id)]).factor_id
            f42_contract_info_id=self.get_record(old_franchisee['f42_contract_info_id'][0],'ifs.contract.info',{})
            f43_contract_info_id=self.get_record(old_franchisee['f43_contract_info_id'][0],'ifs.contract.info',{})
            p01_contract_info_id=self.get_record(old_franchisee['p01_contract_info_id'][0],'ifs.contract.info',{})
            f42_contract_info_id['partner_one']="{},{}".format("ifs.partner.franchisee",franchisee.id)
            f43_contract_info_id['partner_one']="{},{}".format("ifs.partner.franchisee",franchisee.id)
            p01_contract_info_id['partner_one']="{},{}".format("ifs.partner.factor",factor.id)
            p01_contract_info_id['partner_two']="{},{}".format("ifs.partner.franchisee",franchisee.id)
            f42_contract_info_id['template_id']=f42_contract_info_id['template_id'][0]
            f43_contract_info_id['template_id']=f43_contract_info_id['template_id'][0]
            p01_contract_info_id['template_id']=p01_contract_info_id['template_id'][0]
            franchisee.sudo().write({
                'p01_contract_info_id':request.env['ifs.contract.info'].create(p01_contract_info_id).id,
                'f42_contract_info_id':request.env['ifs.contract.info'].create(f42_contract_info_id).id,
                'f43_contract_info_id':request.env['ifs.contract.info'].create(f43_contract_info_id).id,
            })
            franchisee.sudo().active_franchisee()
        
    
    @http.route('/migrate_supplier', type='http', auth="user")
    def migrate_supplier(self, **kwargs):
        invite_suppliers = rpc.do_rpc({}, 'search_read', {
            "model": "ifs.gar.invite.supplier",
            "fields": ["name","phone","email","business_id", "code", "company_name", "create_date", "cut_off_time", "factor_id", "id", "message_main_attachment_id", "other_fee_remark", "principal_id", "sales_id", "state", "supplier_id", "website_id", "write_date"],
            "domain": [],
        }).get("records")
        print(invite_suppliers)
        for invite_supplier in invite_suppliers:
            if invite_supplier['phone']=='18695310111':
                continue
            credit_no=invite_supplier['business_id'][1].split(' ')[0]
            invite_supplier_id = request.env['ifs.gar.invite.supplier'].sudo().search([('credit_no','=',credit_no)])
            if invite_supplier_id.exists():
                continue
            invite_supplier['website_id']=invite_supplier['website_id'][0]
            factor=request.env['ifs.partner.factor'].search([('business_id.company_id.name','=',invite_supplier['factor_id'][1])])
            invite_supplier['factor_id']=factor.id
            
            business_id = self.sync_business_registration(credit_no)
            invite_supplier['business_id']=business_id.id
            if invite_supplier['sales_id']:
                sales = self.get_record(invite_supplier['sales_id'][0],'ifs.gar.sales',{})
                sales_partner = self.get_record(sales['partner_id'][0],'res.partner',{})
                sales_partner['parent_id']=request.env['res.partner'].search([('name','=',sales_partner['parent_id'][1])]).id
                partner = self.create_partner(sales_partner)
                sales['partner_id'] = partner.id
                sales['phone'] = partner.phone
                sales['email'] = partner.email
                print(sales)
                sales= self.get_sales(sales)
                
                invite_supplier['sales_id'] =sales.id
                # partner.write({'parent_id':sales_partner['parent_id']})
                sales.write({'partner_id':partner.id})
                invite_supplier['sales_id']=sales.id
                # continue
            if invite_supplier['supplier_id']:
                supplier=self.get_record(invite_supplier['supplier_id'][0],'ifs.partner.supplier',{})
                if supplier['account_ids']:
                    supplier_account_ids = rpc.do_rpc({}, 'search_read', {
                        "model": "res.company.account",
                        "fields": ["id","company_id","account_type","name","deposit_bank","account_no"],
                        "domain": [("id","in",supplier["account_ids"])],
                    }).get("records")
                    account_ids=[]
                    for account in supplier_account_ids:
                        account['company_id']=business_id.company_id.id
                        account_id = request.env['res.company.account'].sudo().create(account)
                        account_ids.append(account_id.id)
                    supplier['account_ids']=[fields.Command.set(account_ids)]

                supplier['f42_contract_info_id']=False
                supplier['f43_contract_info_id']=False
                supplier['t17_contract_info_id']=False
                supplier['t21_contract_info_id']=False
                supplier['business_id']=business_id.id
                if supplier['contact_partner_id']:
                    contact_partner = self.get_record(supplier['contact_partner_id'][0],'res.partner',{})
                    contact_partner['parent_id']=business_id.company_id.partner_id.id
                    contact_partner_id = self.create_partner(contact_partner)

                    supplier['contact_partner_id']=contact_partner_id.id
                if supplier['financial_manager_id']:
                    financial_manager = self.get_record(supplier['financial_manager_id'][0],'res.partner',{})
                    financial_manager['country_id']=financial_manager['country_id'][0]
                    financial_manager['state_id']=financial_manager['state_id'][0]
                    
                    financial_manager['parent_id']=business_id.company_id.partner_id.id
                    financial_manager_id = self.create_partner(financial_manager)
                    supplier['financial_manager_id']=financial_manager_id.id
                supplier_id = request.env['ifs.partner.supplier'].search([('business_id.credit_no','=',credit_no)])
                if supplier_id:
                    invite_supplier['supplier_id']=supplier_id.id
                else:
                    supplier_id = request.env['ifs.partner.supplier'].sudo().create(supplier)
                    invite_supplier['supplier_id']=supplier_id.id
            invite_supplier_id = request.env['ifs.gar.invite.supplier'].sudo().search([('credit_no','=',credit_no)])
           
            principal = self.get_record(invite_supplier['principal_id'][0],"res.partner",{})
            # if principal['name']=='汪贵生':
            #     principal['phone']='18909582228'
            # if principal['name']=='曹春雷':
            #     principal['phone']='18695310111'
            principal["parent_id"]=business_id.company_id.partner_id.id
            
            if isinstance(principal['state_id'],list):
                principal['state_id']=principal['state_id'][0]
            if isinstance(principal['country_id'],list):
                principal['country_id']=principal['country_id'][0]
            principal_id = self.create_partner(principal)

            invite_supplier['principal_id']=principal_id.id
            invite_supplier['phone']=principal_id.phone
            invite_supplier['email']=principal_id.email
            invite_supplier_id=request.env['ifs.gar.invite.supplier'].sudo().create(invite_supplier)

            employee = request.env['hr.employee'].sudo().search([
                ('company_id', '=', business_id.company_id.id),
                ('name', '=', business_id.principal_id.name),
                ('work_phone', '=', principal_id.phone)
            ])
            employee.write({
                'idcard_id': request.env['hr.employee.idcard'].sudo().create({
                    'name':principal_id.name,
                    'idcard_no':principal_id.idcard.card_no,
                    'gender':principal_id.gender,
                    'address':principal_id.idcard.address,
                    'authority':principal_id.idcard.authority,
                    'start_date':principal_id.idcard.start_date,
                    'end_date':principal_id.idcard.end_date,
                    'front_image':principal_id.idcard.idcard_front_image,
                    'back_image':principal_id.idcard.idcard_back_image,
                    'handle_image':principal_id.idcard.idcard_handle_image
                }).id
            })
        self.migrate_supplier_contract()
        return request.make_json_response(invite_suppliers)
    
    def get_factor_list(self,obj):
        # sales = rpc.do_rpc({}, 'search_read', {
        #     "model": "ifs.gar.sales",
        #     "fields": ["partner_id", "current_entry_step", "f42_contract_info_id", "f43_contract_info_id", "family_address", "franchisee_suggest", "id", "industry", "industry_resources", "industry_time", "p01_contract_info_id", "state"],
        #     "domain": [],
        #     "context":{
        #         'allowed_company_ids':[2],
        #         # 'company_id':2
        #     }
        # })

        result = rpc.do_rpc({}, 'search_read', {
            "model": "ifs.partner.factor",
            "fields": ["abbr", "business_address","business_id", "contact_partner_id", "credit_no", "expiration", "financial_manager_id",
                       "id", "offiaccount_id", "org_auth_state", "sign_name", "state", "token","business_license","deposit_license","signature","account_ids"],
            "domain": [],
        })
        factors={}
        for factor in result.get("records"):
            partner_factor = request.env['ifs.partner.factor'].sudo().search([('business_id.credit_no','=',factor["credit_no"])])
            if partner_factor.exists():
                continue
            business = self.get_record(factor["business_id"][0],"res.company.business.registration",{})
            company = self.get_record(business["company_id"][0],"res.company",{})
            principal_id = self.get_record(company["principal_id"][0],"res.partner",{})
            
            business_id = self.sync_business_registration(factor["credit_no"])
            factor_account_ids = rpc.do_rpc({}, 'search_read', {
                "model": "res.company.account",
                "fields": ["id","company_id","account_type","name","deposit_bank","account_no"],
                "domain": [("id","in",factor["account_ids"])],
            }).get("records")
            account_ids=[]
            for account in factor_account_ids:
                account['company_id']=business_id.company_id.id
                account_id = request.env['res.company.account'].sudo().create(account)
                account_ids.append(account_id.id)
            
            if isinstance(principal_id["country_id"],list):
                principal_id["country_id"]=principal_id["country_id"][0]
            if isinstance(principal_id["state_id"],list):
                principal_id["state_id"]=principal_id["state_id"][0]
            principal_id["parent_id"]=business_id.company_id.partner_id.id
            card_no=principal_id['idcard']
            principal_id.pop('idcard')

            principal = self.create_partner(principal_id)
            # principal.add_idcard(idcard)
            idcard = self.get_idcard(card_no)
            principal.write({
                'idcard':idcard.id,
                'is_company':False
            })
            # principal_id["idcard"]=request.env["res.partner.idcard"].create(idcard).id
            
            business_id.write({
                "principal_id":principal.id,
                "account_ids":[fields.Command.link(account_ids)]
            })
            contact_partner_id = self.get_record(factor["contact_partner_id"][0],"res.partner",obj.get("res.partner"))
            contact_partner_id["parent_id"]=business_id.company_id.partner_id.id
            if isinstance(contact_partner_id["country_id"],list):
                contact_partner_id["country_id"]=contact_partner_id["country_id"][0]
            if isinstance(contact_partner_id["state_id"],list):
                contact_partner_id["state_id"]=contact_partner_id["state_id"][0]
            financial_manager_id = self.get_record(factor["financial_manager_id"][0],"res.partner",obj.get("res.partner"))
            financial_manager_id["parent_id"]=business_id.company_id.partner_id.id
            if isinstance(financial_manager_id["country_id"],list):
                financial_manager_id["country_id"]=financial_manager_id["country_id"][0]
            if isinstance(financial_manager_id["state_id"],list):
                financial_manager_id["state_id"]=financial_manager_id["state_id"][0]

            factor["contact_partner_id"] = self.create_partner(contact_partner_id).id
            factor["business_id"] = business_id.id
            factor["financial_manager_id"] = self.create_partner(financial_manager_id).id
            factor["offiaccount_id"] = 1
            factor["credit_no"]=business["credit_no"]
            factor["business_address"]=business["address"]
            factor["phone"]=principal_id["phone"]
            factor["email"]=principal_id["email"]
            factor_id = request.env["ifs.partner.factor"].sudo().create(factor)
            
            employee = request.env['hr.employee'].sudo().search([
                ('company_id', '=', business_id.company_id.id),
                ('name', '=', business_id.principal_id.name),
                ('work_phone', '=', principal_id["phone"])
            ])
            employee.write({
                'idcard_id': request.env['hr.employee.idcard'].sudo().create({
                    'name':principal.name,
                    'idcard_no':idcard.card_no,
                    'gender':principal.gender,
                    'address':idcard.address,
                    'authority':idcard.authority,
                    'start_date':idcard.start_date,
                    'end_date':idcard.end_date,
                    'front_image':idcard.idcard_front_image,
                    'back_image':idcard.idcard_back_image,
                    'handle_image':idcard.idcard_handle_image
                }).id
            })
        return factors

    @http.route('/migrate_franchisee', type='http', auth="user")
    def get_franchisee_list(self):
        factors = rpc.do_rpc({}, 'search_read', {
            "model": "ifs.partner.factor",
            "fields": ["abbr", "business_address","business_id", "contact_partner_id", "credit_no", "expiration", "financial_manager_id",
                       "id", "offiaccount_id", "org_auth_state", "sign_name", "state", "token","business_license","deposit_license","signature","account_ids"],
            "domain": [],
        }).get("records")
        franchisee_columns=["business_address","business_id", "contact_partner_id", "credit_no", "financial_manager_id","industry","industry_selection","industry_time","industry_resources",
                       "id", "org_auth_state", "state","business_license","deposit_license","account_ids","franchisee_suggest","family_address","current_entry_step",
                       "f42_contract_info_id","f43_contract_info_id","p01_contract_info_id"]
        for source_factor in factors:
            invite_franchisees  = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.gar.invite.franchisee",
                "fields": ["area_agency_fee", "area_id", "area_nature", "business_id", "code", "company_name", "country_id",
                        "currency_id", "factor_id", "first_year_base_service_fee", "first_year_trade_service_fee", "follow_up_base_service_fee", 
                        "follow_up_trade_service_fee", "franchisee_id", "franchisee_type", "id", "principal_id", "state", "state_id","credit_no"],
                "domain": [("factor_id","=",source_factor['id'])],
            })
            new_factor = request.env["ifs.partner.factor"].search([('credit_no','=',source_factor['credit_no'])])
            for invite_franchisee in invite_franchisees.get("records"):
                franchisee = request.env['ifs.partner.franchisee'].sudo().search([('business_id.credit_no','=',invite_franchisee["credit_no"])])
                if franchisee.exists():
                    continue
                
                business_id = self.sync_business_registration(invite_franchisee["credit_no"])
                invite_franchisee['area_id']=invite_franchisee['area_id'][0]
                invite_franchisee['business_id']=business_id.id
                invite_franchisee['country_id']=invite_franchisee['country_id'][0]
                invite_franchisee['currency_id']=invite_franchisee['currency_id'][0]
                invite_franchisee['factor_id']=new_factor.id
                
                invite_franchisee['principal_id']=invite_franchisee['principal_id'][0]
                invite_franchisee['state_id']=invite_franchisee['state_id'][0]
                
                franchisee = rpc.do_rpc({}, 'search_read', {
                    "model": "ifs.partner.franchisee",
                    "fields": franchisee_columns,
                    "domain": [("id","=",invite_franchisee['franchisee_id'][0])],
                }).get("records")[0]

                business = self.get_record(franchisee["business_id"][0],"res.company.business.registration",{})
                company = self.get_record(business["company_id"][0],"res.company",{})
                principal_id = self.get_record(company["principal_id"][0],"res.partner",{})
                if principal_id['name']=='汪贵生':
                    continue
                    principal_id['phone']='18909582228'
                if principal_id['name']=='曹春雷':
                    continue
                    principal_id['phone']='18695310111'
                principal_id["country_id"]=principal_id["country_id"][0]
                card_no=False
                if principal_id["idcard"]:
                    card_no=principal_id["idcard"][1]
                
                principal_id["parent_id"]=business_id.company_id.partner_id.id
                principal_id.pop("idcard")
                principal = self.create_partner(principal_id)
                if card_no:
                    principal.write({
                        'idcard':self.get_idcard(card_no).id,
                    })
                    
                update_map={
                    "principal_id":principal.id,
                }
                business_id.company_id.write(update_map)
                if franchisee['account_ids']:
                    account_ids=[]
                    franchisee_account_ids = self.get_account(franchisee['account_ids'])
                    for account in franchisee_account_ids:
                        account['company_id']=business_id.company_id.id
                        account_id = request.env['res.company.account'].sudo().create(account)
                        account_ids.append(account_id.id)
                    # update_map['account_ids']=[fields.Command.link(account_ids)]
                    business_id.company_id.write({
                        'account_ids':[fields.Command.set(account_ids)]
                    })
                else:
                    franchisee.pop('account_ids')
                    franchisee.pop('deposit_license')            
                if franchisee['contact_partner_id']:
                    contact_partner = self.get_record(franchisee['contact_partner_id'][0],"res.partner",{})
                    contact_partner['country_id']=contact_partner['country_id'][0]
                    contact_partner["parent_id"]=business_id.company_id.partner_id.id
                    if contact_partner["idcard"]:
                        contact_partner["idcard"]=self.get_idcard(contact_partner["idcard"][1]).id
                    franchisee['contact_partner_id']=self.create_partner(contact_partner).id
                if franchisee['financial_manager_id']:
                    financial_manager = self.get_record(franchisee['financial_manager_id'][0],"res.partner",{})
                    financial_manager['country_id']=financial_manager['country_id'][0]
                    financial_manager["parent_id"]=business_id.company_id.partner_id.id
                    if financial_manager["idcard"]:
                        financial_manager["idcard"]=self.get_idcard(financial_manager["idcard"][1]).id
                    franchisee['financial_manager_id']=self.create_partner(financial_manager).id
                franchisee['business_id']=business_id.id
                franchisee["credit_no"]=business["credit_no"]
                franchisee["business_address"]=business["address"]
                franchisee["phone"]=principal_id["phone"]
                franchisee["email"]=principal_id["email"]
                if franchisee['f42_contract_info_id']:
                    franchisee['f42_contract_info_id']=False
                if franchisee['f43_contract_info_id']:
                    franchisee['f43_contract_info_id']=False
                if franchisee['p01_contract_info_id']:
                    franchisee['p01_contract_info_id']=False
                franchisee_id = request.env['ifs.partner.franchisee'].sudo().create(franchisee)
                invite_franchisee['franchisee_id']=franchisee_id.id
                invite_franchisee['factor_id']=new_factor.id
                invite_franchisee['principal_id']=principal.id
                invite_franchisee['invite_franchisee_type']=invite_franchisee['franchisee_type']
                invite_franchisee["phone"]=principal_id["phone"]
                invite_franchisee["email"]=principal_id["email"]
                invite_franchisee_id = request.env["ifs.gar.invite.franchisee"].sudo().create(invite_franchisee)
                employee = request.env['hr.employee'].sudo().search([
                    ('company_id', '=', business_id.company_id.id),
                    ('name', '=', business_id.principal_id.name),
                    ('work_phone', '=', business_id.principal_id.phone)
                ])
                employee.write({
                    'idcard_id': request.env['hr.employee.idcard'].sudo().create({
                        'name':principal.name,
                        'idcard_no':principal.idcard.card_no,
                        'gender':principal.gender,
                        'address':principal.idcard.address,
                        'authority':principal.idcard.authority,
                        'start_date':principal.idcard.start_date,
                        'end_date':principal.idcard.end_date,
                        'front_image':principal.idcard.idcard_front_image,
                        'back_image':principal.idcard.idcard_back_image,
                        'handle_image':principal.idcard.idcard_handle_image
                    }).id
                })
                print(invite_franchisee_id)
        self.migrate_franchisee_contract()
        return request.make_json_response({})
    
    @http.route('/migrate_merchant', type='http', auth="user")
    def migrate_merchant(self):
        invite_merchants = rpc.do_rpc({}, 'search_read', {
            "model": "ifs.gar.invite.merchant",
            "fields": ["id","business_id", "principal_id", "website_id", "factor_supplier_id", "state", "muti_factor", "create_date", "write_date", "merchant_id", 
                       "currency_id","approval_opinion", "factor_suggest", "reject_reason", "remark", "approved_quota"],
            "domain": [],
        }).get('records')
        for invite_merchant in invite_merchants:
            print("++++++++++++++++++++++++{}+++++++++++++++++++++++++++++".format(str(invite_merchant['merchant_id'])))
            invite_merchant['website_id']=invite_merchant['website_id'][0]
            invite_merchant['currency_id']=invite_merchant['currency_id'][0]
            credit_no = invite_merchant['business_id'][1].split(' ')[0]
            factor_supplier = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.gar.partner.factor.supplier",
                "fields": ["id","factor_id","supplier_id"],
                "domain": [('id','=',invite_merchant['factor_supplier_id'][0])],
            }).get('records')[0]
            factor_supplier_id = request.env['ifs.gar.partner.factor.supplier'].sudo().search([('factor_id.name','=',factor_supplier['factor_id'][1]),('supplier_id.name','=',factor_supplier['supplier_id'][1])])
            invite_merchant['factor_supplier_id']=factor_supplier_id.id
            principal = self.get_record(invite_merchant['principal_id'][0],'res.partner',{})
            invite_merchant['principal_id']=principal
            principal['country_id']=principal['country_id'][0]
            if isinstance(principal['state_id'],list):
                principal['state_id']=principal['state_id'][0]
            card_no = False
            if isinstance(principal['idcard'],list):
                card_no=principal['idcard'][1]
                principal.pop('idcard')
                # principal['idcard']=self.get_idcard(principal['idcard'][1])
            business_id = self.sync_business_registration(credit_no)
            invite_merchant['business_id']=business_id.id
            principal["parent_id"]=business_id.company_id.partner_id.id
            principal_id=self.create_partner(principal)
            if card_no:
                principal_id.write({'idcard':self.get_idcard(card_no)})
            invite_merchant['principal_id']=principal_id.id
            invite_id = request.env['ifs.gar.invite.merchant'].sudo().search([('business_id.credit_no','=',credit_no)])
            merchant_id = invite_merchant['merchant_id']
            if not invite_id.exists():
                invite_merchant["phone"]=principal_id["phone"]
                invite_merchant["email"]=principal_id["email"]
                invite_merchant.pop('merchant_id')
                invite_id = request.env['ifs.gar.invite.merchant'].sudo().create(invite_merchant)
            employee = request.env['hr.employee'].sudo().search([
                ('company_id', '=', business_id.company_id.id),
                ('name', '=', business_id.principal_id.name),
                ('work_phone', '=', principal["phone"])
            ])
            if principal_id.idcard.exists():
                employee_idcard=request.env['hr.employee.idcard'].sudo().search([('idcard_no','=',principal_id.idcard.card_no)])
                if not employee_idcard.exists():
                    employee_idcard=request.env['hr.employee.idcard'].sudo().create({
                        'name':principal_id.name,
                        'idcard_no':principal_id.idcard.card_no,
                        'gender':principal_id.gender,
                        'address':principal_id.idcard.address,
                        'authority':principal_id.idcard.authority,
                        'start_date':principal_id.idcard.start_date,
                        'end_date':principal_id.idcard.end_date,
                        'front_image':principal_id.idcard.idcard_front_image,
                        'back_image':principal_id.idcard.idcard_back_image,
                        'handle_image':principal_id.idcard.idcard_handle_image
                    })
                employee.write({
                    'idcard_id': employee_idcard.id
                })
            if not merchant_id:
                continue

            merchant = self.get_record(merchant_id[0],'ifs.partner.merchant',{})
            merchant['invite_id']=invite_id.id
            merchant['business_id']=business_id.id
            merchant['currency_id']=merchant['currency_id'][0]
            if merchant['contact_partner_id']:
                contact_partner = self.get_record(merchant['contact_partner_id'][0],'res.partner',{})
                contact_partner["parent_id"]=business_id.company_id.partner_id.id  
                merchant['contact_partner_id'] =self.create_partner(contact_partner).id
            if merchant['contact_person_one_id']:
                contact_person_one = self.get_record(merchant['contact_person_one_id'][0],'res.partner',{})
                contact_person_one["parent_id"]=business_id.company_id.partner_id.id 
                merchant['contact_person_one_id'] = self.create_partner(contact_person_one).id
            if merchant['contact_person_two_id']:
                contact_person_two = self.get_record(merchant['contact_person_two_id'][0],'res.partner',{})
                contact_person_two["parent_id"]=business_id.company_id.partner_id.id 
                merchant['contact_person_two_id']=self.create_partner(contact_person_two).id
            if merchant['guarantor_id']:
                guarantor = self.get_record(merchant['guarantor_id'][0],'res.partner',{})
                guarantor["parent_id"]=business_id.company_id.partner_id.id
                merchant['guarantor_id']=  self.create_partner(guarantor).id 
            if merchant['financial_manager_id']:
                financial_manager = self.get_record(merchant['financial_manager_id'][0],'res.partner',{})
                financial_manager["parent_id"]=business_id.company_id.partner_id.id
                merchant['financial_manager_id']=  self.create_partner(financial_manager).id
            merchant_id  = request.env['ifs.partner.merchant'].sudo().search([('business_id.credit_no','=',credit_no)])
            if not merchant_id.exists():
                if not merchant['account_no']:
                    merchant.pop('account_no')
                    merchant.pop('account_name')
                    merchant.pop('deposit_license')
                merchant_id = request.env['ifs.partner.merchant'].sudo().create(merchant)
                invite_id.write({'merchant_id':merchant_id.id})
            supplier_merchants = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.gar.partner.supplier.merchant",
                "fields": ["id","merchant_id","supplier_id","currency_id","sub_loan_account_ids"],
                "domain": [('business_id.credit_no','=',credit_no)],
            }).get('records')
            
            if len(supplier_merchants)==0:
                continue
            for supplier_merchant in supplier_merchants:
                supplier_id = request.env['ifs.partner.supplier'].sudo().search([('business_id.company_id.name','=',supplier_merchant['supplier_id'][1])])
                factor_merchant_id = request.env['ifs.gar.partner.factor.merchant'].sudo().search([('merchant_id','=',merchant_id.id),('factor_id','=',factor_supplier_id.factor_id.id)])
                if not factor_merchant_id.exists():
                    factor_merchant_id=request.env['ifs.gar.partner.factor.merchant'].create({
                        'merchant_id':merchant_id.id,
                        'factor_id':factor_supplier_id.factor_id.id
                    })
                    
                loan_account = rpc.do_rpc({}, 'search_read', {
                    "model": "ifs.gar.loan.account",
                    "fields": ["id","state","active","factor_merchant_id","approved_quota","available_quota","freeze_quota","used_quota","penalty_interest_rate","damages_interest_rate","is_compound_interest"],
                    "domain": [("factor_merchant_id.merchant_id.business_id.credit_no","=",merchant_id.business_id.credit_no)],
                }).get('records')[0]
                loan_account_id = request.env['ifs.gar.loan.account'].sudo().search([('factor_merchant_id','=',factor_merchant_id.id)])
                if not loan_account_id.exists():
                    loan_account['factor_merchant_id']=factor_merchant_id.id
                    loan_account_id=request.env['ifs.gar.loan.account'].create(loan_account)
                    
                supplier_merchant_id = request.env['ifs.gar.partner.supplier.merchant'].sudo().search([('supplier_id','=',supplier_id.id),('merchant_id','=',merchant_id.id)])
                if not supplier_merchant_id.exists():
                    supplier_merchant_id = request.env['ifs.gar.partner.supplier.merchant'].sudo().create({
                        'merchant_id':merchant_id.id,
                        'supplier_id':supplier_id.id
                    })

                for sub_loan_account_id in supplier_merchant['sub_loan_account_ids']:
                    sub_loan_account=self.get_record(sub_loan_account_id,'ifs.gar.sub.loan.account',{})

                    sub_loan_account_id = request.env['ifs.gar.sub.loan.account'].sudo().search([('supplier_merchant_id','=',supplier_merchant_id.id)])
                    if not sub_loan_account_id.exists():
                        sub_loan_account['loan_account_id']=loan_account_id.id
                        sub_loan_account['supplier_merchant_id']=supplier_merchant_id.id
                        sub_loan_account.pop('bill_ids')
                        request.env['ifs.gar.sub.loan.account'].sudo().create(sub_loan_account) 
        self.migrate_merchant_contract()
        return request.make_json_response({})
    
    def create_partner(self,map):
        partner = request.env['res.partner'].sudo().search([('name','=',map['name']),('parent_id','=',map['parent_id'])])
        idcard = False
        if 'idcard' in map.keys() and isinstance(map['idcard'],list):
            card_no=map['idcard'][1]
            idcard=self.get_idcard(card_no)
            map.pop('idcard')
        if 'country_id' in map.keys() and isinstance(map['country_id'],list):
            map['country_id']=map['country_id'][0]
        if 'state_id' in map.keys() and isinstance(map['state_id'],list):
            map['state_id']=map['state_id'][0]
        if 'area_id' in map.keys() and isinstance(map['area_id'],list):
            map['area_id']=map['area_id'][0]

        if partner.exists():
            map1={}
            for key in map.keys():
                if map.get(key):
                    map1[key]=map.get(key)
            partner.write(map1)
        else:
            # print(">>>>>>>>>>>",map['name'],map['parent_id'])
            partner = request.env['res.partner'].sudo().create(map)
        if idcard:
            partner.write({
                'idcard':idcard.id
            })
        return partner
    def get_sales(self,map):
        sales = request.env['ifs.gar.sales'].search([('partner_id','=',map['partner_id'])])
        if sales:
            return sales
        else:
            sales = request.env['ifs.gar.sales'].create(map)
            return sales
    
    
    def get_idcard(self,cardno):
        cardno=cardno[0:18]
        idcard = request.env['res.partner.idcard'].search([('card_no','=',cardno)])
        if idcard:
            return idcard
        else:
            result = rpc.do_rpc({}, 'search_read', {
                "model": "res.partner.idcard",
                "fields": ["address", "authority", "card_no", "create_date", "end_date", "id", "message_main_attachment_id", "start_date", "write_date", "idcard_front_image", "idcard_back_image", "idcard_handle_image"],
                "domain": [("card_no", "=", cardno)],
            })
            if result != None and result.get("records")[0]:
                idcard = request.env['res.partner.idcard'].create(result.get("records")[0])
                return idcard
            else:
                return None
                
    def get_contract(self,contract_id):
        result = rpc.do_rpc({}, 'search_read', {
                "model": "ifs.contract.info",
                "fields": ["code", "create_date", "expire_date", "full_name", "id", "identity_card", "identity_type", "jzq_apply_no", "jzq_contract_dl_url", "jzq_contract_view_url", "jzq_state", "message_main_attachment_id", "name", "params", "partner_four", "partner_one", "partner_three", "partner_two", "report_content", "sign_date", "state", "template_id", "write_date"],
                "domain": [("id", "=", contract_id)],
            })
        contract = result.get("records")[0]
        code = contract['code'][0:3]
        contract['template_id']=request.env['ifs.contract.template'].search([('code','=',code)]).id
        return request.env['ifs.contract.info'].create(contract)    
    
    def get_account(self, ids):
        result = rpc.do_rpc({}, 'search_read', {
            "model": "res.company.account",
            "fields": ["id", "company_id", "account_type", "name", "deposit_bank", "account_no"],
            "domain": [("id", "in", ids)],
        })
        return result.get("records")
    
    def get_record(self, id, model, map):
        res_partner_columns = ["active", "additional_info", "area_id", "city", "color", "comment", "company_id", "company_name", "country_id", "create_date",  "date",  "email", "email_normalized", "employee", "function", "gender", "id", "idcard", "industry_id", "is_default_addr", "is_published", "lang", "message_bounce",
                               "message_main_attachment_id", "mobile", "name", "parent_id", "partner_gid", "partner_latitude", "partner_longitude", "phone", "phone_sanitized", "ref", "signup_expiration", "signup_token", "signup_type", "state_id", "street", "street2", "title", "type", "tz", "union_id", "vat", "website", "website_id", "write_date", "zip"]
        res_company_business_registration_columns = ["address", "authority", "business_date_from", "business_date_to", "business_scope",  "capital", "code", "company_id", "company_type", "credit_no", "establish_date",
                                                     "id", "is_on_stock", "issue_date", "last_sync_time", "legal_person", "logo_url", "org_code", "parent_id", "province", "real_captical", "revoke_date", "stock_number", "stock_type", "updated_date"]
        wechat_offiaccount_config_columns = ["app_id", "create_date", "id", "is_default", "message_encoding_aeskey", "message_encrypt_mode",
                                             "message_format", "message_main_attachment_id", "message_token", "name", "offiaccount_type", "qr_login_id", "secret", "website_id", "write_date"]
        res_company_columns = ["base_onboarding_company_state", "company_details", "create_date", "currency_id", "email", "external_report_layout_id", "font", "hr_presence_control_email_amount", "hr_presence_control_ip_list", "iap_enrich_auto_done", "id", "layout_background", "logo_web", "mobile", "name", "paperformat_id", "parent_id", "partner_gid",
                               "partner_id", "phone", "primary_color", "principal_id", "report_footer", "report_header", "resource_calendar_id", "secondary_color", "sequence", "snailmail_color", "snailmail_cover", "snailmail_duplex", "social_facebook", "social_github", "social_instagram", "social_linkedin", "social_twitter", "social_youtube", "website_id", "write_date"]
        res_partner_idcard_columns=["address", "authority", "card_no", "create_date", "end_date", "id", "message_main_attachment_id", "start_date", "write_date","idcard_front_image","idcard_back_image","idcard_handle_image"]
        website_columns=["auth_signup_uninvited", "auto_redirect_lang", "cdn_activated", "cdn_filters", "cdn_url", "company_id", "configurator_done", "cookies_bar", "create_date", "custom_code_footer", "custom_code_head", "default_lang_id", "domain", "google_analytics_key", "google_maps_api_key", "google_search_console", "has_social_default_image", "id", "name", "robots_txt", "sequence", "social_facebook", "social_github", "social_instagram", "social_linkedin", "social_twitter", "social_youtube", "specific_user_account", "theme_id", "user_id", "write_date"]
        res_users_columns=["action_id", "active", "company_id", "create_date", "create_uid", "id", "login", "notification_type", "odoobot_failed", "odoobot_state", "partner_id", "password", "share", "signature", "totp_secret", "website_id", "write_date"]
        res_partner_idcard_image_columns=["id","idcard","name","can_image_1024_be_zoomed"]
        ifs_contract_info_columns=["params","partner_one_signature","partner_two_signature","code", "create_date", "expire_date", "full_name", "id", "identity_card", "identity_type", "jzq_apply_no", "jzq_contract_dl_url", "jzq_contract_view_url", "jzq_state", "message_main_attachment_id", "name", "params", "partner_four", "partner_one", "partner_three", "partner_two", "report_content", "sign_date", "state", "template_id", "write_date","contract"]
        ifs_gar_sales_columns=["code", "create_date",  "current_entry_step", "f42_contract_info_id", "f43_contract_info_id", "family_address", "franchisee_suggest", "id", "idcard_expiry_date", "industry", "industry_resources", "industry_time", "message_main_attachment_id", "p01_contract_info_id", "partner_id", "state", "write_date"]
        # res_company_account_columns=["id","company_id","account_type","name","deposit_bank","account_no"]
        ifs_partner_supplier_columns=["abbr", "approved_quota", "business_address", "business_id", "code", "contact_partner_id", "create_date", "current_entry_step", "cut_off_time", "f42_contract_info_id", "f43_contract_info_id", "financial_manager_id", "id", "idcard_expiry_date", "org_auth_state", "product_scope", "state", "t17_contract_info_id", "t21_contract_info_id", "write_date","deposit_license","business_license","account_ids"]
        ifs_partner_merchant_columns=["abbr","account_name","account_no","account_type","accounts_payable","accounts_receivable","approve_time","area_pay","business_address","business_area",
                           "business_cost","business_debt","business_id","business_income","company_equipment_assets","company_equipment_assets_caption","company_equipment_assets_value",
                           "company_housing_assets","company_housing_assets_value","company_vehicle_assets","company_vehicle_assets_value","contact_partner_id",
                           "contact_person_one_id","contact_person_one_relationship","contact_person_two_id","contact_person_two_relationship","contract_expire_date",
                           "create_date","currency_id","current_entry_step","deposit_bank","deposit_license","display_name","employee_quantity","enterprise_property_certificate",
                           "family_address","fere_id","financial_manager_id","guarantee_amount","guarantee_remarks","guarantor_family_address","guarantor_guarantee_amount",
                           "guarantor_guarantee_remarks","guarantor_highest_education","guarantor_housing_assets","guarantor_id","guarantor_loan_amount","guarantor_loan_remarks",
                           "guarantor_nation","guarantor_other_assets","guarantor_other_assets_remarks","guarantor_vehicle_assets","half_year_assets_gains_losses_sheet",
                           "half_year_balance_sheet","half_year_cash_flow_sheet","hand_real_capital","has_message","highest_education","housing_assets","id","intangible_capital",
                           "invite_id","is_agree_all","is_agree_guarantor_inform_one","is_agree_guarantor_inform_three","is_agree_guarantor_inform_two","is_guarantor_has_guarantee",
                           "is_guarantor_has_housing_assets","is_guarantor_has_loan","is_guarantor_has_other_assets","is_guarantor_has_vehicle_assets","is_guarantor_married","is_has_guarantee",
                           "is_has_housing_assets","is_has_loan","is_has_other_assets","is_has_vehicle_assets","is_legal_person","is_married","legal_person_property_certificate","loan_amount",
                           "loan_remarks",	"nation","org_auth_state","other_assets","other_assets_remarks","payrolls","social_insurance_number","social_insurance_pay","state","stock_value",
                           "vehicle_assets","write_date","business_license","charter","lease_contract","office_area_picture","reception_picture",]
        # "account_name","account_no","deposit_bank"
        ifs_gar_sub_loan_account_columns=["id","loan_account_id","supplier_merchant_id","state","active","approved_quota","available_quota","freeze_quota","used_quota","bill_ids",
                    "penalty_interest_rate","damages_interest_rate","is_compound_interest","idcard_expiry_date","account_type",]
        ifs_gar_loan_account_columns=["id","state","active","factor_merchant_id","approved_quota","available_quota","freeze_quota","used_quota","penalty_interest_rate","damages_interest_rate","is_compound_interest"]
        ifs_gar_loan_account_bill_columns=["code","state","start_bill_date","cut_off_time","bill_date","repayment_date","currency_id","freeze_quota","used_quota","loan_amount","repayment_amount","pending_amount","pending_interest","bill_amount","bill_log_ids"]
        ifs_gar_loan_account_bill_log_columns=["order_id","id","code","bill_id","order_id","operate_type","amount","remark","bill_log_date","prev_log_id"]
        model_fields={
            "res.partner":res_partner_columns,
            "res.company.business.registration":res_company_business_registration_columns,
            "wechat.offiaccount.config":wechat_offiaccount_config_columns,
            "res.company":res_company_columns,
            "res.partner.idcard":res_partner_idcard_columns,
            "website":website_columns,
            "res.users":res_users_columns,
            "res.partner.idcard.image":res_partner_idcard_image_columns,
            "ifs.contract.info":ifs_contract_info_columns,
            "ifs.gar.sales":ifs_gar_sales_columns,
            "ifs.partner.supplier":ifs_partner_supplier_columns,
            "ifs.partner.merchant":ifs_partner_merchant_columns,
            "ifs.gar.sub.loan.account":ifs_gar_sub_loan_account_columns,
            "ifs.gar.loan.account":ifs_gar_loan_account_columns,
            "ifs.gar.loan.account.bill":ifs_gar_loan_account_bill_columns,
            "ifs.gar.loan.account.bill.log":ifs_gar_loan_account_bill_log_columns
        }
        if map.get(id):
            return map.get(id)
        else:
            result = rpc.do_rpc({}, 'search_read', {
                "model": model,
                "fields": model_fields[model],
                "domain": [("id", "=", id)],
            }).get("records")
            map[id]=result[0]
            return result[0]

    def sync_business_registration(self, credit_no):
        business = request.env['res.company.business.registration'].sudo().search(
            [('credit_no', '=', credit_no)])
        if business.exists():
            return business
        raw_business = rpc.do_rpc({}, 'search_read', {
            "model": 'res.company.business.registration',
            "fields": ["name","address", "authority", "business_date_from", "business_date_to", "business_scope",  "capital", "code", "company_type", "credit_no", "establish_date",
                       "id", "is_on_stock", "issue_date", "last_sync_time", "legal_person", "logo_url", "org_code", "province", "real_captical", "revoke_date", "stock_number", "stock_type", "updated_date"],
            "domain": [("credit_no", "=", credit_no)],
        }).get("records")[0]
        return request.env['res.company.business.registration'].sudo().create(raw_business)


    @http.route('/migrate17_factor', type='http', auth="user")
    def migrate17_factor(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_factor(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_factor?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_franchisee")
    
    @http.route('/migrate17_franchisee', type='http', auth="user")
    def migrate17_franchisee(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_franchisee(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_franchisee?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_supplier")
    
    @http.route('/migrate17_supplier', type='http', auth="user")
    def migrate17_supplier(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_supplier(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_supplier?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_merchant")
    
    async def my_async_function(self):
        migrate_data17.migrate_merchant()
    
    @http.route('/migrate17_merchant', type='http', auth="user")
    def migrate17_merchant(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_merchant(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_merchant?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_trade_order")
    
        
    @http.route('/migrate17_trade_order', type='http', auth="user")
    def migrate17_trade_order(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_trade_order(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_trade_order?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_lawfirm")
    
    # 律师事务所
    @http.route('/migrate17_lawfirm', type='http', auth="user")
    def migrate17_lawfirm(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_lawfirm(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_lawfirm?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return "success"
    
    # 保险公司
    @http.route('/migrate17_insurance', type='http', auth="user")
    def migrate17_insurance(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_insurance(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_insurance?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return "success"

    # 投保人
    @http.route('/migrate17_insurant', type='http', auth="user")
    def migrate17_insurant(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_insurant(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_insurant?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_channelsp")
        
    # 服务商
    @http.route('/migrate17_channelsp', type='http', auth="user")
    def migrate17_channelsp(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_channelsp(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_channelsp?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return request.redirect("/migrate17_insured")
    
    # 被保人
    @http.route('/migrate17_insured', type='http', auth="user")    
    def migrate17_insured(self,**kw):
        limit = 1
        offset = 0
        if kw.get("limit"):
            limit = int(kw.get("limit"))
        if kw.get("offset"):
            offset = int(kw.get("offset"))
        length = migrate_data17.migrate_insured(limit,offset)
        if length > offset:
            return request.redirect("/migrate17_insured?limit=%s&offset=%s" % (limit,offset+limit))
        else:
            return "success"
    
    
    @http.route('/migrate17_test', type='http', auth="user")
    def migrate17_test(self,**kw):
        comm_var = {}
        migrate_data17.do_rpc(comm_var,'ifs.contract.info',['id'],limit=1)
        contract = migrate_data17.get_attachment(comm_var,'ifs.contract.info',70,'contract')
        with open('aaaaaaaaaaa.pdf', 'wb') as file:
            file.write(base64.b64decode(contract))
        return "success"