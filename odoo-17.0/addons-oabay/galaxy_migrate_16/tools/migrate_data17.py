# -*- coding: utf-8 -*-

import json
import time
import base64
import requests
import io
import asyncio
from odoo.http import request
from odoo import _, api, models, fields, Command

BASE_URL = 'https://demo.ysb.yzbfp.com'
DB_NAME = 'ysb_2'
LOGIN = 'ferrenliu@163.com'
PASSWORD = '123456'

model_fields = {
    'ifs.partner.factor':['name','ifs_company_id']
}


def do_rpc_login(comm_var,db, login, password):
    result = requests.post(''.join([
        BASE_URL, '/web/session/authenticate']), json={
            'db': db,
                'login': login,
                'password': password,
            'params': {
                'db': db,
                'login': login,
                'password': password,
            }
    })
    for cookie in result.cookies:
        if cookie.name == 'session_id':
            comm_var['session_id'] = cookie.value
    return json.loads(result.text).get('result')

def do_rpc(comm_var, model,fields,domain=[],limit=800,offset=0,order="id ASC",timeout=(300,300)):
    if not comm_var.get('session_id'):
        do_rpc_login(comm_var, DB_NAME, LOGIN, PASSWORD)
    
    with  requests.post(f"{BASE_URL}/web/dataset/call_kw/{model}/web_search_read",
        headers={"X-Openerp-Session-Id":comm_var.get('session_id')},timeout=timeout,
        json={
            "id": 19,
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": "web_search_read",
                "args": [],
                "kwargs": {
                    "domain": domain,
                    "fields": fields,
                    "limit":limit,
                    "offset":offset,
                    "order":order
                }
            }
        }) as response:
        content = b""
        for chunk in response.iter_content(chunk_size=64):
            content += chunk
        result = content.decode('utf-8')
    return json.loads(result).get('result')
# base_company_fields = ['partner_id','logo','seq_code','street','phone','email','name','company_registry','org_auth_state','business_address','doc_ids','business_license','charter','deposit_license','company_code','business_date_from','business_date_to','capital','real_captical','business_date','legal_name',
#                        'legal_phone','legal_email','principal_name','finance_id','finance_name','finance_phone','version','seal','food_production_license_no',
#                        'food_production_license','guarantor_employee_id','reception_picture','office_area_picture','lease_contract','half_year_balance_sheet','half_year_cash_flow_sheet','half_year_assets_gains_losses_sheet','enterprise_property_certificate',
#                        'root_employee_id','legal_id_number','legal_address','legal_authority','legal_idcard_expiry_date','legal_front_image','legal_back_image','need_fetch']
base_company_attachment_fields = ['logo','legal_front_image','legal_back_image']
base_company_fields = ['partner_id','seq_code','street','phone','email','name','company_registry','org_auth_state','business_address','doc_ids','company_code','business_date_from','business_date_to','capital','real_captical','business_date','legal_name',
                       'legal_phone','legal_email','principal_name','finance_id','finance_name','finance_phone','version','seal','food_production_license_no','guarantor_employee_id','root_employee_id','legal_id_number','legal_address','legal_authority','legal_idcard_expiry_date','need_fetch'] + base_company_attachment_fields


base_company_partner_fields = ['ifs_partner_factor_ids','ifs_partner_franchisee_ids','ifs_partner_funder_ids','ifs_partner_lawfirm_ids','ifs_partner_merchant_ids','ifs_partner_supplier_ids','ifs_partner_insurance_ids','ifs_partner_insurant_ids','ifs_partner_insured_ids','ifs_partner_channelsp_ids']

step_minin_fields = ['current_model']
contract_fields = ['name','code','partner_one','partner_one_signature','partner_one_liveness_video','partner_one_best_frame','partner_two','partner_two_signature','partner_two_liveness_video','partner_two_best_frame','partner_three','partner_three_signature','partner_three_liveness_video','partner_three_best_frame',
                   'partner_four','partner_four_signature','partner_four_liveness_video','partner_four_best_frame','params','report_content','template_content','validity_period','full_name','identity_card','identity_type','jzq_apply_no','jzq_contract_view_url','jzq_contract_dl_url','jzq_state']
bank_fields = ['state','country','name','zip','city','email','phone','bic','active']

def get_model_fields(model_name):
    model = request.env[model_name]
    fields = []
    for field_name, field_info in model.fields_get().items():
        if field_info.get('type') != 'binary' and not model._fields[field_name].compute and field_name not in ['create_uid','write_uid','message_follower_ids','message_ids','website_message_ids','activity_ids']:
            fields.append(field_name)
    return fields

def migrate_base_company_doc(comm_var,ifs_company_id:int,base_company):
    mapping = request.env['ifs.base.company']._doc_mapping()

    for field,name in mapping.items():
        company_doc = request.env['ifs.base.company.doc'].sudo().search([('ifs_company_id','=',base_company.id),('name','=',name)])
        if not company_doc.exists():
            # print(field+'   '+name)
            try:
                doc_data = do_rpc(comm_var,'ifs.base.company.doc',['id','name','doc'],domain=[('ifs_company_id','=',ifs_company_id),('name','=',name)]).get('records')
            except requests.exceptions.ChunkedEncodingError as e:
                doc_data = do_rpc(comm_var,'ifs.base.company.doc',['id','name'],domain=[('ifs_company_id','=',ifs_company_id),('name','=',name)]).get('records')[0]
                doc = get_attachment(comm_var,'ifs.base.company.doc',doc_data.get('id'),'doc')
                request.env['ifs.base.company.doc'].sudo().create({
                    'ifs_company_id':base_company.id,
                    'name':doc_data['name'],
                    'doc':doc
                })
                continue
            if len(doc_data) == 0:
                continue
            doc_data = doc_data[0]
            request.env['ifs.base.company.doc'].sudo().create({
                'ifs_company_id':base_company.id,
                'name':doc_data['name'],
                'doc':doc_data['doc']
            })

def migrate_attachment(comm_var,res_id,record):
    att_fields = []
    att_data = {}
    for field_name, field_info in record.fields_get().items():
        if field_info.get('type') == 'binary':
            att_fields.append(field_name)
    for field in att_fields:
        if not record[field]:
            att_data[field] = get_attachment(comm_var,record._name,res_id,field)
            # try:
            #     binary = do_rpc(comm_var,record._name,[field],domain=[('id','=',res_id)]).get('records')[0]
            #     att_data[field] =binary[field]
            # except requests.exceptions.ChunkedEncodingError as e:
            #     att_data[field] = get_attachment(comm_var,record._name,res_id,field)
    if len(att_data) != 0:
        record.sudo().write(att_data)
def get_attachment(comm_var,model,res_id,field):
    with requests.get(f'{BASE_URL}/web/content?model={model}&id={res_id}&field={field}',headers={"X-Openerp-Session-Id":comm_var.get('session_id')},stream=True,allow_redirects=True) as response:
        if response.status_code == 404:
            return False
        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            file_content += chunk
    return base64.b64encode(file_content).decode('utf-8')

def migrate_entry_merchant_contract(comm_var,entry_merchant_data,entry_merchant):
    t18_template = request.env['ifs.contract.template'].retrieve_by_code('T18',factor_id = entry_merchant.invite_id.factor_id.id,supplier_id = entry_merchant.invite_id.supplier_id.id)
    f41_template = request.env['ifs.contract.template'].retrieve_by_code('F41',factor_id = entry_merchant.invite_id.factor_id.id,supplier_id = entry_merchant.invite_id.supplier_id.id)
    f42_template = request.env['ifs.contract.template'].retrieve_by_code('F42',factor_id = entry_merchant.invite_id.factor_id.id,supplier_id = entry_merchant.invite_id.supplier_id.id)
    f43_template = request.env['ifs.contract.template'].retrieve_by_code('F43',factor_id = entry_merchant.invite_id.factor_id.id,supplier_id = entry_merchant.invite_id.supplier_id.id)
    contract_fields = get_model_fields('ifs.contract.info')
    contract_fields = [item for item in contract_fields if item not in ['partner_one','partner_two','partner_three','partner_four','template_id']]
    if entry_merchant_data.get('t18_contract_info_id'):
        t18_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_merchant_data.get('t18_contract_info_id')[0])]).get('records')[0]
        if not t18_contract_info.get('params'):
            t18_contract_info['params'] = '{}'
        t18_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
            'partner_two': '%s,%d' % (entry_merchant.factor_id._name, entry_merchant.factor_id.id),
            'partner_two_signature': entry_merchant.factor_id.signature,
            'template_id': t18_template.id,
            **t18_contract_info
        })
        migrate_attachment(comm_var,t18_contract_info.get('id'),t18_contract)
        entry_merchant.sudo().write({
            't18_contract_info_id':t18_contract.id
        })
    if entry_merchant_data.get('f41_contract_info_id'):
        f41_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_merchant_data.get('f41_contract_info_id')[0])]).get('records')[0]
        if not f41_contract_info.get('params'):
            f41_contract_info['params'] = '{}'
        f41_contract = request.env['ifs.contract.info'].create({
            'template_id': f41_template.id,
            'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
            **f41_contract_info
        })
        migrate_attachment(comm_var,f41_contract_info.get('id'),f41_contract)
        entry_merchant.sudo().write({
            'f41_contract_info_id':f41_contract.id
        })
    if entry_merchant_data.get('f42_contract_info_id'):
        f42_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_merchant_data.get('f42_contract_info_id')[0])]).get('records')[0]
        f42_contract = request.env['ifs.contract.info'].create({
            'template_id': f42_template.id,
            'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
            **f42_contract_info
        })
        migrate_attachment(comm_var,f42_contract_info.get('id'),f42_contract)
        entry_merchant.sudo().write({
            'f42_contract_info_id':f42_contract.id
        })
    if entry_merchant_data.get('f43_contract_info_id'):
        f43_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_merchant_data.get('f43_contract_info_id')[0])]).get('records')[0]
        f43_contract = request.env['ifs.contract.info'].create({
            'template_id': f43_template.id,
            'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
            **f43_contract_info
        })
        migrate_attachment(comm_var,f43_contract_info.get('id'),f43_contract)
        entry_merchant.sudo().write({
            'f43_contract_info_id':f43_contract.id
        })
    if entry_merchant_data.get('guarantor_contract_info_id'):
        guarantor_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_merchant_data.get('guarantor_contract_info_id')[0])]).get('records')[0]
        guarantor_contract = request.env['ifs.contract.info'].create({
            'template_id': f41_template.id,
            'partner_one': '%s,%d' % (entry_merchant._name, entry_merchant.id),
            **guarantor_contract_info
        })
        migrate_attachment(comm_var,guarantor_contract_info.get('id'),guarantor_contract)
        entry_merchant.sudo().write({
            'guarantor_contract_info_id':guarantor_contract.id
        })

def migrade_trade_order_contract(comm_var,trade_order_data,trade_order):
    trade_order_data = do_rpc(comm_var,'ifs.gar.trade.order',get_model_fields('ifs.gar.trade.order'),domain=[('id','=',trade_order_data.get('id'))]).get('records')[0]
    contract_fields = get_model_fields('ifs.contract.info')
    contract_fields = [item for item in contract_fields if item not in ['partner_one','partner_two','partner_three','partner_four','template_id']]
    factor = trade_order.factor_id
    supplier = trade_order.supplier_id
    merchant = trade_order.merchant_id
    d08_template = request.env['ifs.contract.template'].retrieve_by_code('D08', factor.id)
    t19_template = request.env['ifs.contract.template'].retrieve_by_code('T19', factor.id)
    d09_template = request.env['ifs.contract.template'].retrieve_by_code('D09', factor.id)
    t20_template = request.env['ifs.contract.template'].retrieve_by_code('T20', factor.id)
    c13_template = request.env['ifs.contract.template'].retrieve_by_code('C13', factor.id)
    c14_template = request.env['ifs.contract.template'].retrieve_by_code('C14', factor.id)
    update_info = {'write_date':trade_order_data.get('write_date')}
    if trade_order_data.get('d08_contract_info_id'):
        d08_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('d08_contract_info_id')[0])]).get('records')[0]
        d08_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (factor._name, factor.id),
            'partner_two': '%s,%d' % (supplier._name, supplier.id),
            'template_id': d08_template.id,
            **d08_contract_info
        })
        migrate_attachment(comm_var,d08_contract_info.get('id'),d08_contract)
        update_info['d08_contract_info_id'] = d08_contract
        
    if trade_order_data.get('t19_contract_info_id'):
        t19_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('t19_contract_info_id')[0])]).get('records')[0]
        t19_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (factor._name, factor.id),
            'partner_two': '%s,%d' % (supplier._name, supplier.id),
            'partner_three': '%s,%d' % (merchant._name, merchant.id),
            'template_id': t19_template.id,
            **t19_contract_info
        })
        migrate_attachment(comm_var,t19_contract_info.get('id'),t19_contract)
        update_info['t19_contract_info_id'] = t19_contract.id

    if trade_order_data.get('d09_contract_info_id'):
        d09_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('d09_contract_info_id')[0])]).get('records')[0]
        d09_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (merchant._name, merchant.id),
            'partner_two': '%s,%d' % (factor._name, factor.id),
            'template_id': d09_template.id,
            **d09_contract_info
        })
        migrate_attachment(comm_var,d09_contract_info.get('id'),d09_contract)
        update_info['d09_contract_info_id'] = d09_contract.id

    if trade_order_data.get('t20_contract_info_id'):
        t20_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('t20_contract_info_id')[0])]).get('records')[0]
        t20_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (factor._name, factor.id),
            'partner_two': '%s,%d' % (merchant._name, merchant.id),
            'partner_three': '%s,%d' % (supplier._name, supplier.id),
            'template_id': t20_template.id,
            **t20_contract_info
        })
        migrate_attachment(comm_var,t20_contract_info.get('id'),t20_contract)
        update_info['t20_contract_info_id'] = t20_contract.id
        
    if trade_order_data.get('c13_contract_info_id'):
        c13_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('c13_contract_info_id')[0])]).get('records')[0]
        c13_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (supplier._name, supplier.id),
            'partner_two': '%s,%d' % (factor._name, factor.id),
            'template_id': c13_template.id,
            **c13_contract_info
        })
        migrate_attachment(comm_var,c13_contract_info.get('id'),c13_contract)
        update_info['c13_contract_info_id'] = c13_contract.id
        
    if trade_order_data.get('c14_contract_info_id'):
        c14_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',trade_order_data.get('c14_contract_info_id')[0])]).get('records')[0]
        c14_contract = request.env['ifs.contract.info'].create({
            'partner_one': '%s,%d' % (merchant._name, merchant.id),
            'partner_two': '%s,%d' % (factor._name, factor.id),
            'template_id': c14_template.id,
            **c14_contract_info
        })
        migrate_attachment(comm_var,c14_contract_info.get('id'),c14_contract)
        update_info['c14_contract_info_id'] = c14_contract.id
    trade_order.sudo().write(update_info)

def migrate_entry_lawfirm_contract(comm_var,entry_lawfirm_data,entry_lawfirm):
    contract_fields = get_model_fields('ifs.contract.info')
    contract_fields = [item for item in contract_fields if item not in ['partner_one','partner_two','partner_three','partner_four','template_id']]
    update_info = {
        'write_date':entry_lawfirm_data.get('write_date')
    }
    if entry_lawfirm_data.get('p10_contract_info_id'):
        update_info['p10_contract_info_id'] = entry_lawfirm.invite_id.p10_contract_info_id.id,
    if entry_lawfirm_data.get('f42_contract_info_id'):
        f42_template = request.env['ifs.contract.template'].retrieve_by_code('F42', entry_lawfirm.invite_id.factor_id.id)
        f42_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_lawfirm_data.get('f42_contract_info_id')[0])]).get('records')[0]
        f42_contract = request.env['ifs.contract.info'].create({
            'template_id': f42_template.id,
            'partner_one': '%s,%d' % (entry_lawfirm._name, entry_lawfirm.id),
            **f42_contract_info
        })
        migrate_attachment(comm_var,entry_lawfirm_data.get('f42_contract_info_id')[0],f42_contract)
        update_info['f42_contract_info_id'] = f42_contract
    if entry_lawfirm_data.get('f43_contract_info_id'):
        f43_template = request.env['ifs.contract.template'].retrieve_by_code('F43', entry_lawfirm.invite_id.factor_id.id)
        f43_contract_info = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_lawfirm_data.get('f43_contract_info_id')[0])]).get('records')[0]
        f43_contract = request.env['ifs.contract.info'].create({
            'template_id': f43_template.id,
            'partner_one': '%s,%d' % (entry_lawfirm._name, entry_lawfirm.id),
            **f43_contract_info
        })
        migrate_attachment(comm_var,entry_lawfirm_data.get('f43_contract_info_id')[0],f43_contract)
        update_info['f43_contract_info_id'] = f43_contract
    entry_lawfirm.sudo().write(update_info)


def migrate_company_hr(comm_var,company_registry):
    base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company_registry)])
    hr_employee_infos = do_rpc(comm_var,'hr.employee',['name','login','mobile_phone','work_email','work_position_ids','state','is_root','user_partner_id'],domain=[('company_id.company_registry','=',company_registry)])
    for hr_employee_info in hr_employee_infos.get('records'):
        if hr_employee_info.get('name') == 'Administrator':
            continue
        hr_employee = request.env['hr.employee'].sudo().search([('login','=',hr_employee_info.get('login'))])
        # if True == hr_employee.is_root:
        #     continue
        # partner_id = hr_employee.user_id.partner_id
        # user_id = hr_employee.user_id
        # hr_employee.unlink()
        # user_id.unlink()
        # partner_id.unlink()
        
        if hr_employee.exists():
            continue
        if hr_employee_info.get('is_root'):
            default_wp = request.env['ifs.work.position'].sudo().search([('company_id', '=', base_company.company_id.id),('code', '=', 'SYSTEM')], limit=1)
            hr_employee_info['work_position_ids'] = [Command.link(default_wp.id)] if default_wp else False
            del hr_employee_info['user_partner_id']
            hr_employee = request.env['hr.employee'].sudo().create({
                **hr_employee_info,
                'company_id':base_company.company_id.id,
                'user_partner_id':base_company.legal_id.id,
            })
            base_company.sudo().write({
                'root_employee_id':hr_employee.id,
            })
        else:
            work_position_ids = []
            work_position_infos = do_rpc(comm_var,'ifs.work.position',['color','name','code','need_one_time_passwd'],domain=[('id','in',hr_employee_info.get('work_position_ids'))]).get('records')
            for work_position_info in work_position_infos:
                work_position_info['company_id'] = base_company.company_id.id
                work_position = request.env['ifs.work.position'].sudo().search([('code','=',work_position_info.get('code')),('company_id','=',base_company.company_id.id)])
                if not work_position.exists():
                    work_position = request.env['ifs.work.position'].sudo().create(work_position_info)
                work_position_ids.append(work_position.id)
            user_partner = request.env['res.partner'].sudo().search([('complete_name','=',hr_employee_info.get('user_partner_id')[1]),('parent_id','=',base_company.company_id.partner_id.id)])
            if not user_partner.exists():
                user_partner_info = do_rpc(comm_var,'res.partner',['name','company_registry','type','street','city','email','phone','mobile','commercial_company_name','active','is_company','partner_share','email_normalized','default_pwd'],domain=[('id','=',hr_employee_info.get('user_partner_id')[0])]).get('records')[0]
                user_partner_info['complete_name'] = hr_employee_info.get('user_partner_id')[1]
                user_partner_info['parent_id'] = base_company.company_id.partner_id.id
                user_partner = request.env['res.partner'].sudo().create(user_partner_info)
            hr_employee_info['work_position_ids'] = [Command.set(work_position_ids)]
            hr_employee_info['user_partner_id'] = user_partner.id
            hr_employee_info['company_id'] = base_company.company_id.id
            hr_employee = request.env['hr.employee'].sudo().create(hr_employee_info)
            
def migrate_factor_solution(comm_var,company_registry):
    factor = request.env['ifs.partner.factor'].sudo().search([('company_registry','=',company_registry)])
    solutions = do_rpc(comm_var,'ifs.gar.partner.fee.solution',['name','seq_code'],domain=[('factor_id.company_registry','=',company_registry)])
    for solution_info in solutions.get('records'):
        solution = request.env['ifs.gar.partner.fee.solution'].sudo().search([('name','=',solution_info.get('name'))])
        if not solution.exists():
            solution = request.env['ifs.gar.partner.fee.solution'].sudo().create({
                'name':solution_info.get('name'),
                'factor_id':factor.id
            })
            solution.sudo().write({'seq_code':solution_info.get('seq_code')})
        solution_vers = do_rpc(comm_var,'ifs.gar.partner.fee.solution.ver',['fee_solution_id','version','description','contract_content','rule_ids'],domain=[('factor_id.company_registry','=',company_registry),('fee_solution_id','=',solution_info.get('id'))]).get('records')
        for solution_ver_info in solution_vers:
            solution_ver = request.env['ifs.gar.partner.fee.solution.ver'].sudo().search([('fee_solution_id','=',solution.id),('version','=',solution_ver_info.get('version'))])
            if not solution_ver.exists():
                solution_ver = request.env['ifs.gar.partner.fee.solution.ver'].sudo().create({
                    'fee_solution_id':solution.id,'version':solution_ver_info.get('version'),'description':solution_ver_info.get('description'),'contract_content':solution_ver_info.get('contract_content')
                })
                for rule_id in solution_ver_info.get('rule_ids'):
                    rule_info = do_rpc(comm_var,'ifs.gar.partner.fee.rule',['fee_type','fee_mode'],domain=[('id','=',rule_id)]).get('records')[0]
                    fee_type_info = do_rpc(comm_var,'ifs.gar.partner.fee.type',['name','code','color','remark'],domain=[('id','=',rule_info.get('fee_type')[0])]).get('records')[0]
                    fee_type = request.env['ifs.gar.partner.fee.type'].sudo().search([('name','=',fee_type_info.get('name')),('code','=',fee_type_info.get('code'))])
                    if not fee_type.exists():
                        fee_type = request.env['ifs.gar.partner.fee.type'].sudo().create(fee_type_info)
                    fee_mode_model = rule_info.get('fee_mode').split(',')[0]
                    fee_mode_id = rule_info.get('fee_mode').split(',')[1]
                    fee_mode_info = do_rpc(comm_var,fee_mode_model,get_model_fields(fee_mode_model),domain=[('id','=',fee_mode_id)]).get('records')[0]
                    if fee_mode_info.get('currency_id'):
                        fee_mode_info['currency_id'] = factor.company_id.currency_id.id
                    fee_mode = request.env[fee_mode_model].sudo().create(fee_mode_info)
                    request.env['ifs.gar.partner.fee.rule'].sudo().create({
                        'ver_solution_id':solution_ver.id,
                        'fee_type':fee_type.id,
                        'fee_mode':'%s,%d' % (fee_mode._name,fee_mode.id)
                    })
         
        

# def get_user(comm_var,res_id,name):
#     user = request.env['res.users'].sudo().search([('name','=',name)])

#     if not user.exists():
#         user_info = do_rpc(comm_var,'res.users',['company_id','partner_id','password','new_password','active','login','signature','share','notification_type'],domain=[('id','=',res_id)])
#         hr_employee_info = do_rpc(comm_var,'hr.employee',['name','login','mobile_phone','work_email','work_position_ids','state','company_id','user_partner_id','is_root'],domain=[('user_id','=',res_id)])
#         print('')

def migrate_factor(limit=1,offset=0):
    comm_var = {}
    fields = ['ifs_company_id','state','signature','sign_name','token','expiration','legal_phone','legal_email']
    result = do_rpc(comm_var, 'ifs.partner.factor',fields  ,limit=limit,offset=offset)
    
    records = result.get('records')
    for record in records:
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields, domain=[('id','=',record.get('ifs_company_id')[0])]).get('records')[0]
        print(company.get('name'))
        company_registry = record.get('ifs_company_id')[1].split(' /')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company_registry)])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,record['ifs_company_id'][0], base_company)
            company_data = {}
            for key in base_company_fields:
                company_data[key] = record.get(key)
            base_company.sudo().write(company_data)
        factor = request.env['ifs.partner.factor'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not factor.exists():
            factor = request.env['ifs.partner.factor'].sudo().create({
                'ifs_company_id':base_company.id,
                'state':record.get('state'),
                'signature':record.get('signature'),
                'sign_name':record.get('sign_name'),
                'token':record.get('token'),
                'expiration':record.get('expiration'),
            })
        migrate_company_hr(comm_var,company.get('company_registry'))
        migrate_factor_solution(comm_var,company.get('company_registry'))
        
    return result.get('length')

def entry_franchisee_action_approve(entry_id):
    partner_bank_info = {
        'bank_id': entry_id.bank_id.id,
        'acc_number': entry_id.acc_number,
        'currency_id': entry_id.company_id.currency_id.id,
    }
    # 把进件向导录入的信息更新到当前进件的公司全局信息中
    entry_id.ifs_company_id.write({
        'phone': entry_id.phone,
        'email': entry_id.email,
        'business_address': entry_id.business_address,
        'business_license': entry_id.business_license,
        'deposit_license': entry_id.deposit_license,
        'bank_ids': [Command.update(entry_id.ifs_company_id.acquiescence_bank_id.id, partner_bank_info)] if entry_id.ifs_company_id.acquiescence_bank_id else [Command.create(partner_bank_info)],
        'reception_picture': entry_id.reception_picture,
        'office_area_picture': entry_id.office_area_picture,
    })
    partner_franchisee_sudo = entry_id.env['ifs.partner.franchisee'].sudo()
    franchisee = partner_franchisee_sudo.search([
        ('ifs_company_id', '=', entry_id.ifs_company_id.id)], limit=1)
    if not franchisee.exists():
        franchisee = partner_franchisee_sudo.create({
            'ifs_company_id': entry_id.ifs_company_id.id,
        })

    factor_franchisee = request.env['ifs.gar.partner.factor.franchisee'].sudo().search([('factor_id','=',entry_id.factor_id.id),('franchisee_id','=',franchisee.id)])
    if not factor_franchisee.exists():
        factor_franchisee = entry_id.env['ifs.gar.partner.factor.franchisee'].create({
            'entry_id': entry_id.id,
            'factor_id': entry_id.factor_id.id,
            'franchisee_id': franchisee.id,
        })
    
    # 更新法人信息
    idcard = request.env['hr.employee.idcard'].sudo().search([('idcard_no','=',entry_id.legal_id_number)])
    if not idcard.exists():
        idcard = entry_id.env['hr.employee.idcard'].sudo(
        ).create_legal_from_entry(entry_id)
    entry_id.root_employee_id.sudo().write({
        'gender': idcard.gender,
        'birthday': idcard.birthday,
        'idcard_id': idcard.id,
    })
    entry_id.write({
        'state': 'approval',
        'franchisee_id': franchisee.id,
    })
    factor_franchisee = entry_id.env['ifs.gar.partner.factor.franchisee'].search([
        ('entry_id', '=', entry_id.id)], limit=1)
    factor_franchisee.write({
        'p01_contract_info_id': entry_id.p01_contract_info_id.id,
        'f42_contract_info_id': entry_id.f42_contract_info_id.id,
        'f43_contract_info_id': entry_id.f43_contract_info_id.id,
    })

def migrate_franchisee(limit=1,offset=0):
    comm_var = {}
    invite_franchisee_fields = ['p01_contract_info_id','factor_id','state','ifs_company_id','franchisee_id','entry_date','franchisee_code','entry_ids','p01_contract_info_id','seq_code']
    entry_franchisee_fields = ['state','business_license','phone','email','business_address','legal_front_image','legal_back_image','legal_name','legal_id_number','legal_nationality','legal_gender','legal_birthday','legal_address','legal_authority','legal_start_date','legal_end_date','acc_number',
                    'deposit_license','reception_picture','office_area_picture','review_date','reject_reason','p01_contract_info_id','f42_contract_info_id','f43_contract_info_id']
    franchisee_fields = ['industry','industry_selection','industry_time','industry_resources','franchisee_suggest','family_address']
    invite_franchisees = do_rpc(comm_var,'ifs.gar.invite.franchisee',invite_franchisee_fields  ,domain=[],limit=limit,offset=offset)
    for record in invite_franchisees.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields,domain=[('id','=',record.get('ifs_company_id')[0])]).get('records')[0]
        print(company.get('name'))
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',record.get('company_registry'))])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,record['ifs_company_id'][0],base_company)
        migrate_company_hr(comm_var,company.get('company_registry'))
        factor = request.env['ifs.partner.factor'].sudo().search([('name','=',record.get('factor_id')[1])])
        invite_franchisee = request.env['ifs.gar.invite.franchisee'].sudo().search([('seq_code','=',company.get('seq_code'))])
        if not invite_franchisee.exists():
            invite_franchisee = request.env['ifs.gar.invite.franchisee'].sudo().create({
                'ifs_company_id':base_company.id,
                'factor_id':factor.id,
            })
            invite_franchisee.sudo().write({
                'seq_code':record.get('seq_code')
            })
        """
        if not base_company.root_employee_id.exists():
            default_wp = request.env['ifs.work.position'].sudo().search([
                ('company_id', '=', base_company.company_id.id),
                ('code', '=', 'SYSTEM')
            ], limit=1)
            company = do_rpc(comm_var,'ifs.base.company',fields=['name','seq_code'],domain=[('company_id.company_registry','=',record.get('company_registry'))]).get('records')[0]
            root_employee = request.env['hr.employee'].sudo().create({
                'name': record.get('legal_name'),
                'login': company.get('seq_code'),
                'mobile_phone': record.get('legal_phone'),
                'work_email': record.get('legal_email'),
                'work_position_ids': [Command.link(default_wp.id)] if default_wp else False,
                'state': 'normal',
                'company_id': base_company.company_id.id,
                'user_partner_id': base_company.legal_id.id,
                'is_root': True,
            })
            base_company.sudo().write({
                'root_employee_id':root_employee.id,
            })  
        """
        for entry_id in record.get('entry_ids'):
            entry_franchisee_info = do_rpc(comm_var,'ifs.gar.entry.franchisee',step_minin_fields + get_model_fields('ifs.gar.entry.franchisee'),domain=[('id','=',entry_id)]).get('records')[0]
            entry_franchisee = request.env['ifs.gar.entry.franchisee'].sudo().search([('seq_code','=',entry_franchisee_info.get('seq_code'))])
            if not entry_franchisee.exists():
                entry_franchisee_records = do_rpc(comm_var,'ifs.gar.entry.franchisee',step_minin_fields + entry_franchisee_fields,domain=[('ifs_company_id.company_registry','=',company.get('company_registry'))]).get('records')
                if len(entry_franchisee_records) == 0:
                    continue
                entry_franchisee_info = entry_franchisee_records[0]
                entry_franchisee_info.pop('p01_contract_info_id')
                entry_franchisee_info.pop('f42_contract_info_id')
                entry_franchisee_info.pop('f43_contract_info_id')
                entry_franchisee = request.env['ifs.gar.entry.franchisee'].sudo().create({
                    **entry_franchisee_records[0],
                    'ifs_company_id':base_company.id,
                    'invite_id':invite_franchisee.id
                })
            entry_contracts = do_rpc(comm_var,'ifs.gar.entry.franchisee',['p01_contract_info_id','f42_contract_info_id','f43_contract_info_id'],domain=[('id','=',entry_id)]).get('records')[0]
            if not entry_franchisee.p01_contract_info_id.exists() and entry_contracts.get('p01_contract_info_id'):
                p01_template = request.env['ifs.contract.template'].sudo().search([('code','=','P01')],limit=1)
                p01_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_contracts.get('p01_contract_info_id')[0])]).get('records')[0]
                p01_contract.pop('partner_one')
                p01_contract.pop('partner_two')
                p01_contract_info = request.env['ifs.contract.info'].sudo().create({
                    **p01_contract,
                    'partner_one': '%s,%d' % (factor._name, factor.id),
                    'partner_two': '%s,%d' % (invite_franchisee._name, invite_franchisee.id),
                    'template_id': p01_template.id,
                })
                entry_franchisee.write({
                    'p01_contract_info_id':p01_contract_info.id
                })
            if not not entry_franchisee.f42_contract_info_id.exists() and entry_contracts.get('f42_contract_info_id'):
                f42_template = request.env['ifs.contract.template'].retrieve_by_code('F42',factor_id=factor.id)
                f42_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_contracts.get('f42_contract_info_id')[0])]).get('records')[0]
                f42_contract.pop('partner_one')
                f42_contract_info = request.env['ifs.contract.info'].create({
                    'name': f42_template.name,
                    'template_id': f42_template.id,
                    'partner_one': '%s,%d' % (entry_franchisee._name, entry_franchisee.id)
                })
                entry_franchisee.write({
                    'f42_contract_info_id':f42_contract_info.id
                })
            if not not entry_franchisee.f43_contract_info_id.exists() and entry_contracts.get('f43_contract_info_id'):
                f43_template = request.env['ifs.contract.template'].retrieve_by_code('F43',factor_id=factor.id)
                f43_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',entry_contracts.get('f43_contract_info_id')[0])]).get('records')[0]
                f43_contract.pop('partner_one')
                f43_contract_info = request.env['ifs.contract.info'].create({
                    'name': f43_template.name,
                    'template_id': f43_template.id,
                    'partner_one': '%s,%d' % (entry_franchisee._name, entry_franchisee.id)
                })
                entry_franchisee.write({
                    'f43_contract_info_id':f43_contract_info.id
                })
        franchisee = request.env['ifs.partner.franchisee'].sudo().search([('ifs_company_id.company_registry','=',company.get('company_registry'))])
        if not franchisee.exists():
            franchisee_records = do_rpc(comm_var,'ifs.partner.franchisee',franchisee_fields,domain=[('ifs_company_id.company_registry','=',company.get('company_registry'))]).get('records')
            if len(franchisee_records) == 0:
                continue
            franchisee = request.env['ifs.partner.franchisee'].sudo().create({
                **franchisee_records[0],
                'ifs_company_id':base_company.id
            })

        if record.get('state') == 'ready':
            # entry_franchisee.action_approve()
            entry_franchisee_action_approve(entry_franchisee)
            invite_franchisee.sudo().write({
                'state':'ready'
            })
        
    return invite_franchisees.get('length')
    
def entry_supplier_action_approve(entry_id):
    partner_bank_info = {
        'bank_id': entry_id.bank_id.id,
        'acc_number': entry_id.acc_number,
        'currency_id': entry_id.company_id.currency_id.id,
    }
    partner = entry_id.env['res.partner'].search([
        ('parent_id', '=', entry_id.partner_id.id),
        ('name', '=', entry_id.finance_name)])
    if not partner.exists():
        partner = entry_id.env['res.partner'].create({
            'name': entry_id.finance_name,
            'phone': entry_id.finance_phone,
            'mobile': entry_id.finance_phone,
            'parent_id': entry_id.partner_id.id
        })
    # 把进件向导录入的信息更新到当前进件的公司全局信息中
    entry_id.ifs_company_id.write({
        'finance_id': partner.id,
        'phone': entry_id.phone,
        'email': entry_id.email,
        'business_address': entry_id.business_address,
        'business_license': entry_id.business_license,
        'deposit_license': entry_id.deposit_license,
        'bank_ids': [Command.update(entry_id.ifs_company_id.acquiescence_bank_id.id, partner_bank_info)] if entry_id.ifs_company_id.acquiescence_bank_id else [Command.create(partner_bank_info)],
        'reception_picture': entry_id.reception_picture,
        'office_area_picture': entry_id.office_area_picture,
    })
    factor_supplier_data = {
        'entry_id': entry_id.id,
        'factor_id': entry_id.factor_id.id,
        'franchisee_id': entry_id.franchisee_id.id if entry_id.franchisee_id else False,
        'product_scope': entry_id.product_scope,
    }
    partner_supplier_sudo = entry_id.env['ifs.partner.supplier'].sudo()
    supplier = partner_supplier_sudo.search([
        ('ifs_company_id', '=', entry_id.ifs_company_id.id)], limit=1)
    if not supplier.exists():
        supplier = partner_supplier_sudo.create({
            'ifs_company_id': entry_id.ifs_company_id.id,
        })
    factor_supplier_data.update({
        'supplier_id': supplier.id,
        'cut_off_time': entry_id.invite_id.cut_off_time,
        'cut_off_cron_id': entry_id._create_cut_off_cron(),
        'fee_solution_id': entry_id.invite_id.fee_solution_id.id,
        'total_quota': entry_id.total_quota,
        't17_contract_info_id': entry_id.t17_contract_info_id.id,
        't21_contract_info_id': entry_id.t21_contract_info_id.id,
        'f42_contract_info_id': entry_id.f42_contract_info_id.id,
        'f43_contract_info_id': entry_id.f43_contract_info_id.id,
    })
    factor_supplier = request.env['ifs.gar.partner.factor.supplier'].sudo().search([('factor_id','=',entry_id.factor_id.id),('supplier_id','=',supplier.id)])
    if not factor_supplier.exists():
        entry_id.env['ifs.gar.partner.factor.supplier'].create(
            factor_supplier_data)
    # 更新法人信息
    idcard = entry_id.env['hr.employee.idcard'].sudo(
    ).create_legal_from_entry(entry_id)
    entry_id.root_employee_id.sudo().write({
        'gender': idcard.gender,
        'birthday': idcard.birthday,
        'idcard_id': idcard.id,
    })
    entry_id.sudo().write({
        'state': 'approval',
        'supplier_id': supplier.id,
    })

    
def migrate_supplier(limit=1,offset=0):
    comm_var = {}
    # invite_supplier_fields = ['entry_id','factor_id','franchisee_id','state','entry_date','supplier_id','supplier_code','t17_contract_info_id','cut_off_time','fee_solution_id']
    # entry_supplier_fields = ['state','business_license','phone','email','business_address','product_scope','office_area_picture','legal_front_image','legal_back_image','legal_name','legal_id_number','legal_nationality','legal_gender','legal_birthday','legal_address','legal_authority','legal_start_date','legal_end_date','finance_name','finance_phone',
    #                          'acc_number','deposit_license','review_date','reject_reason','total_quota','t21_contract_info_id','f42_contract_info_id','f43_contract_info_id','bank_id']
    supplier_fields = ['state','sub_loan_account_ids','factor_ids']
    
    invite_suppliers = do_rpc(comm_var,'ifs.gar.invite.supplier',fields = get_model_fields('ifs.gar.invite.supplier'),domain=[],limit=limit,offset=offset)
    for record in invite_suppliers.get('records'): 
        # record = do_rpc(comm_var,'ifs.gar.invite.supplier',fields = get_model_fields('ifs.gar.invite.supplier')  + ['ifs_company_id'],domain=[('id','=',record.get('id'))]).get('records')[0]
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields,domain=[('id','=',record.get('ifs_company_id')[0])]).get('records')[0]
        print(company.get('name')) 
        factor = request.env['ifs.partner.factor'].sudo().search([('name','=',record.get('factor_id')[1])])
        record['factor_id'] = factor.id
        franchisee = False
        if record.get('franchisee_id'):
            franchisee = request.env['ifs.partner.franchisee'].sudo().search([('name','=',record.get('franchisee_id')[1])])
            record['franchisee_id'] = franchisee.id
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',record.get('company_registry'))])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,record['ifs_company_id'][0],base_company)
        record['ifs_company_id'] = base_company.id
        invite_supplier = request.env['ifs.gar.invite.supplier'].sudo().search([('seq_code','=',record.get('seq_code'))])
        if not invite_supplier.exists():
            franchisee_id = False
            if franchisee:
                franchisee_id = franchisee.id
            invite_supplier = request.env['ifs.gar.invite.supplier'].sudo().create({
                'ifs_company_id':base_company.id,
                'factor_id':factor.id,
                'franchisee_id':franchisee_id,
                'state':record.get('state'),
                'invite_date':record.get('invite_date'),
                'create_date':record.get('create_date'),
                'cut_off_time':record.get('cut_off_time'),
            })
            invite_supplier.sudo().write({
                'seq_code':record.get('seq_code')
            })
        fee_solution_id = False
        if record.get('fee_solution_id'):
            fee_solution_info = do_rpc(comm_var,'ifs.gar.partner.fee.solution.ver',fields = get_model_fields('ifs.gar.partner.fee.solution.ver'),domain=[('id','=',record.get('fee_solution_id')[0])]).get('records')[0]
            fee_solution_id = request.env['ifs.gar.partner.fee.solution.ver'].sudo().search([('fee_solution_id.name','=',fee_solution_info.get('fee_solution_id')[1])]).id
        invite_supplier.sudo().write({
            'state':record.get('state'),
            'fee_solution_id':fee_solution_id,
            'write_date':record.get('write_date'),
        })

        migrate_company_hr(comm_var,base_company.company_registry)
        if record.get('t17_contract_info_id'):
            t17_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',record.get('t17_contract_info_id')[0])]).get('records')[0]
            t17_template = request.env['ifs.contract.template'].retrieve_by_code('T17',factor_id=factor.id)
            t17_contract.pop('partner_one')
            t17_contract.pop('partner_two')
            t17_contract_info = request.env['ifs.contract.info'].sudo().create({
                'template_id':t17_template.id,
                'partner_one': '%s,%d' % (invite_supplier._name, invite_supplier.id),
                'partner_two': '%s,%d' % (invite_supplier.factor_id._name, invite_supplier.factor_id.id),
                **t17_contract
            })
            invite_supplier.sudo().write({
                't17_contract_info_id':t17_contract_info.id
            })
        
        for entry_id in sorted(record.get('entry_ids')):
            entry_supplier_data = do_rpc(comm_var,'ifs.gar.entry.supplier', step_minin_fields + get_model_fields('ifs.gar.entry.supplier'),domain=[('id','=',entry_id)]).get('records')[0]
            
            entry_supplier = request.env['ifs.gar.entry.supplier'].sudo().search([('seq_code','=',entry_supplier_data.get('seq_code'))])
        
            if not entry_supplier.exists():
                if entry_supplier_data.get('bank_id'):
                    bank_data = do_rpc(comm_var,'res.bank',fields=bank_fields,domain=[('id','=',entry_supplier_data.get('bank_id')[0])]).get('records')[0]
                    bank = request.env['res.bank'].sudo().search([('name','=',bank_data.get('name'))])
                    if not bank.exists():
                        bank = request.env['res.bank'].sudo().create(bank_data)
                    entry_supplier_data['bank_id'] = bank.id
                t21_contract_info_id = entry_supplier_data.get('t21_contract_info_id')
                f42_contract_info_id = entry_supplier_data.get('f42_contract_info_id')
                f43_contract_info_id = entry_supplier_data.get('f43_contract_info_id')
                entry_supplier_data.pop('t21_contract_info_id')
                entry_supplier_data.pop('f42_contract_info_id')
                entry_supplier_data.pop('f43_contract_info_id')
                if entry_supplier_data.get('last_entry_id'):
                    last_entry_info = do_rpc(comm_var,'ifs.gar.entry.supplier',  get_model_fields('ifs.gar.entry.supplier'),domain=[('id','=',entry_supplier_data.get('last_entry_id')[0])]).get('records')[0]
                    last_entry = request.env['ifs.gar.entry.supplier'].sudo().search([('seq_code','=',last_entry_info.get('seq_code'))])
                    entry_supplier_data['last_entry_id'] = last_entry.id
                entry_supplier = request.env['ifs.gar.entry.supplier'].sudo().create({
                    **entry_supplier_data,
                    'ifs_company_id':base_company.id,
                    'invite_id':invite_supplier.id,
                })
                entry_supplier.sudo().write({
                    'state':entry_supplier_data.get('state')
                })
                migrate_attachment(comm_var,entry_id,entry_supplier)
                if t21_contract_info_id:
                    t21_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',t21_contract_info_id[0])]).get('records')[0]
                    t21_template = request.env['ifs.contract.template'].retrieve_by_code('T21',factor_id=factor.id)
                    t21_contract.pop('partner_one')
                    t21_contract.pop('partner_two')
                    t21_contract.pop('params')
                    t21_contract_info = request.env['ifs.contract.info'].sudo().create({
                        'template_id':t21_template.id,
                        'partner_one': '%s,%d' % (entry_supplier._name, entry_supplier.id),
                        'partner_two': '%s,%d' % (factor._name, factor.id),
                        'params': json.dumps({
                            't17_contract_code': invite_supplier.t17_contract_info_id.code
                        }),
                        **t21_contract
                    })
                    entry_supplier.sudo().write({
                        't21_contract_info_id':t21_contract_info.id
                    })
                if f42_contract_info_id:
                    f42_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',f42_contract_info_id[0])]).get('records')[0]
                    f42_template = request.env['ifs.contract.template'].retrieve_by_code('F42',factor_id=factor.id)
                    f42_contract.pop('partner_one')
                    f42_contract_info = request.env['ifs.contract.info'].create({
                        'name': f42_template.name,
                        'template_id': f42_template.id,
                        'partner_one': '%s,%d' % (entry_supplier._name, entry_supplier.id),
                        **f42_contract
                    })
                    entry_supplier.sudo().write({
                        'f42_contract_info_id':f42_contract_info.id
                    })
                if f43_contract_info_id:
                    f43_contract = do_rpc(comm_var,'ifs.contract.info',contract_fields,domain=[('id','=',f43_contract_info_id[0])]).get('records')[0]
                    f43_template = request.env['ifs.contract.template'].retrieve_by_code('F43',factor_id=factor.id)
                    f43_contract.pop('partner_one')
                    f43_contract_info = request.env['ifs.contract.info'].create({
                        'name': f43_template.name,
                        'template_id': f43_template.id,
                        'partner_one': '%s,%d' % (entry_supplier._name, entry_supplier.id),
                        **f43_contract
                    })
                    entry_supplier.sudo().write({
                        'f43_contract_info_id':f43_contract_info.id
                    })
            
            
        
        if not record.get('supplier_id'):
            continue
        entry_supplier_action_approve(entry_supplier)
        supplier = request.env['ifs.partner.supplier'].sudo().search([('company_registry','=',company.get('company_registry'))])
        supplier_data = do_rpc(comm_var,'ifs.partner.supplier',supplier_fields,domain=[('id','=',record.get('supplier_id')[0])]).get('records')[0]
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].sudo().search([('factor_id','=',factor.id),('supplier_id','=',supplier.id)])
        supplier.sudo().write({
            'state':supplier_data.get('state'),
            'factor_ids':[Command.link(factor_supplier.id)]
        })
        
                
    return invite_suppliers.get('length')

def migrate_merchant(limit=1,offset=0):
    comm_var = {}
    invite_merchant_fields = get_model_fields('ifs.gar.invite.merchant')
    entry_merchant_fields = get_model_fields('ifs.gar.entry.merchant')
    # merchant_fields = get_model_fields('ifs.partner.merchant')
    # entry_merchants = do_rpc(comm_var,'ifs.gar.entry.merchant',entry_merchant_fields).get('records')
    invite_merchants = do_rpc(comm_var,'ifs.gar.invite.merchant',invite_merchant_fields + ['ifs_company_id'],limit=limit,offset=offset)
    for record in invite_merchants.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields ,domain=[('id','=',record.get('ifs_company_id')[0])]).get('records')[0]
        
            
        print(company.get('name')+ ' ' +company.get('company_registry'))
        merchant = request.env['ifs.partner.merchant'].sudo().search([('company_registry','=',company.get('company_registry'))])
        # if merchant.exists():
        #     continue
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,record.get('ifs_company_id')[0],base_company)

        factor = request.env['ifs.partner.factor'].sudo().search([('name','=',record.get('factor_id')[1])])
        if not record.get('supplier_id'):
            continue
        supplier = request.env['ifs.partner.supplier'].sudo().search([('name','=',record.get('supplier_id')[1])])
        record['supplier_id'] = supplier.id
        factor_supplier = request.env['ifs.gar.partner.factor.supplier'].sudo().search([('factor_id','=',factor.id),('supplier_id','=',supplier.id)])
        # invite_merchant = request.env['ifs.gar.invite.merchant'].sudo().search([('factor_id','=',factor.id),('supplier_id','=',supplier.id),('ifs_company_id','=',base_company.id)])
        invite_merchant = request.env['ifs.gar.invite.merchant'].sudo().search([('seq_code','=',record.get('seq_code'))])
        entry_ids = record.get('entry_ids')
        record['ifs_company_id'] = base_company.id
        
        record['factor_id'] = factor.id
        del record['entry_ids']
        merchant_id = record.get('merchant_id')
        record.pop('merchant_id')
        if not invite_merchant.exists():
            invite_merchant = request.env['ifs.gar.invite.merchant'].sudo().create(record)
            invite_merchant.sudo().write({
                'seq_code':record.get('seq_code'),
            })
        migrate_company_hr(comm_var,company.get('company_registry'))
        if len(entry_ids) == 0:
            continue
        entry_merchant_ids = []
        for entry_id in sorted(entry_ids):
            entry_merchant_data = do_rpc(comm_var,'ifs.gar.entry.merchant',entry_merchant_fields,domain=[('id','=',entry_id)]).get('records')[0]
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code','=',entry_merchant_data.get('seq_code'))],limit=1,order="id DESC")
            if entry_merchant.exists():
                migrate_attachment(comm_var,entry_id,entry_merchant)
                migrate_entry_merchant_contract(comm_var,entry_merchant_data,entry_merchant)
                entry_merchant_ids.append(entry_merchant.id)
                continue
            del entry_merchant_data['id']
            del entry_merchant_data['ifs_risk_credits_id']
            del entry_merchant_data['guarantor_ifs_risk_credits_id']
            entry_merchant_data['invite_id'] = invite_merchant.id
            entry_merchant_data['ifs_company_id'] = base_company.id
            if entry_merchant_data.get('business_info_definition_id'):
                business_info_definition = request.env['ifs.gar.entry.definition'].sudo().search([('name','=',entry_merchant_data.get('business_info_definition_id')[1])])
                if not business_info_definition.exists():
                    business_info_definition_data = do_rpc(comm_var,'ifs.gar.entry.definition',['name','params_definition'],domain=[('id','=',entry_merchant_data.get('business_info_definition_id')[0])]).get('records')[0]
                    business_info_definition = request.env['ifs.gar.entry.definition'].sudo().create(business_info_definition_data)
                entry_merchant_data['business_info_definition_id'] = business_info_definition.id
            if entry_merchant_data.get('legal_info_definition_id'):
                legal_info_definition = request.env['ifs.gar.entry.definition'].sudo().search([('name','=',entry_merchant_data.get('legal_info_definition_id')[1])])
                if not legal_info_definition.exists():
                    legal_info_definition_data = do_rpc(comm_var,'ifs.gar.entry.definition',['name','params_definition'],domain=[('id','=',entry_merchant_data.get('legal_info_definition_id')[0])]).get('records')[0]
                    legal_info_definition = request.env['ifs.gar.entry.definition'].sudo().create(legal_info_definition_data)
                entry_merchant_data['legal_info_definition_id'] = legal_info_definition.id
            if entry_merchant_data.get('legal_other_info_definition_id'):
                legal_other_info_definition = request.env['ifs.gar.entry.definition'].sudo().search([('name','=',entry_merchant_data.get('legal_other_info_definition_id')[1])])
                if not legal_other_info_definition.exists():
                    legal_other_info_definition_data = do_rpc(comm_var,'ifs.gar.entry.definition',['name','params_definition'],domain=[('id','=',entry_merchant_data.get('legal_other_info_definition_id')[0])]).get('records')[0]
                    legal_other_info_definition = request.env['ifs.gar.entry.definition'].sudo().create(legal_other_info_definition_data)
                entry_merchant_data['legal_other_info_definition_id'] = legal_other_info_definition.id
            if entry_merchant_data.get('guarantor_info_definition_id'):
                guarantor_info_definition = request.env['ifs.gar.entry.definition'].sudo().search([('name','=',entry_merchant_data.get('guarantor_info_definition_id')[1])])
                if not guarantor_info_definition.exists():
                    guarantor_info_definition_data = do_rpc(comm_var,'ifs.gar.entry.definition',['name','params_definition'],domain=[('id','=',entry_merchant_data.get('guarantor_info_definition_id')[0])]).get('records')[0]
                    guarantor_info_definition = request.env['ifs.gar.entry.definition'].sudo().create(guarantor_info_definition_data)
                entry_merchant_data['guarantor_info_definition_id'] = guarantor_info_definition.id
            del entry_merchant_data['f41_contract_info_id']
            del entry_merchant_data['f42_contract_info_id']
            del entry_merchant_data['f43_contract_info_id']
            del entry_merchant_data['t18_contract_info_id']
            del entry_merchant_data['guarantor_contract_info_id']
            if entry_merchant_data['factor_approval_user_id']:
                factor_approval_user_info = do_rpc(comm_var,'res.users',['company_id'],domain=[('id','=',entry_merchant_data.get('factor_approval_user_id')[0])]).get('records')[0]
                factor_approval_user_company_info = do_rpc(comm_var,'res.company',['name','company_registry'],domain=[('id','=',factor_approval_user_info.get('company_id')[0])]).get('records')[0]
                factor_approval_user_company = request.env['res.company'].sudo().search([('company_registry','=',factor_approval_user_company_info.get('company_registry'))])
                factor_approval_user = request.env['res.users'].sudo().search([('name','=',entry_merchant_data.get('factor_approval_user_id')[1]),('company_id','=',factor_approval_user_company.id)])
                entry_merchant_data['factor_approval_user_id'] = factor_approval_user.id
            if entry_merchant_data['last_entry_id']:
                last_entry_info = do_rpc(comm_var,'ifs.gar.entry.merchant',['name','seq_code'],domain=[('id','=',entry_merchant_data.get('last_entry_id')[0])]).get('records')[0]
                last_entry = request.env['ifs.gar.entry.merchant'].sudo().search([('seq_code','=',last_entry_info.get('seq_code'))],limit=1)
                entry_merchant_data['last_entry_id'] = last_entry.id
            if entry_merchant_data['supplier_approval_user_id']:
                supplier_approval_user_info  = do_rpc(comm_var,'res.users',['company_id'],domain=[('id','=',entry_merchant_data.get('supplier_approval_user_id')[0])]).get('records')[0]
                supplier_approval_user_company_info = do_rpc(comm_var,'res.company',['name','company_registry'],domain=[('id','=',supplier_approval_user_info.get('company_id')[0])]).get('records')[0]
                supplier_approval_user_company = request.env['res.company'].sudo().search([('company_registry','=',supplier_approval_user_company_info.get('company_registry'))])
                supplier_approval_user = request.env['res.users'].sudo().search([('name','=',entry_merchant_data.get('supplier_approval_user_id')[1]),('company_id','=',supplier_approval_user_company.id)])
                entry_merchant_data['supplier_approval_user_id'] = supplier_approval_user.id
            entry_merchant = request.env['ifs.gar.entry.merchant'].sudo().create(entry_merchant_data)
            entry_merchant.sudo().write({
                'seq_code':entry_merchant_data.get('seq_code')
            })
            migrate_attachment(comm_var,entry_id,entry_merchant)
            migrate_entry_merchant_contract(comm_var,entry_merchant_data,entry_merchant)
            entry_merchant_ids.append(entry_merchant.id)

        if not merchant_id:
            continue
        merchant_data = do_rpc(comm_var,'ifs.partner.merchant',get_model_fields('ifs.partner.merchant'),domain=[('id','=',merchant_id[0])]).get('records')[0]
        merchant = request.env['ifs.partner.merchant'].sudo().search([('ifs_company_id','=',base_company.id)])
        if not merchant.exists():
            merchant = request.env['ifs.partner.merchant'].sudo().create({
                'ifs_company_id':base_company.id,
                'state':merchant_data.get('state'),
                'create_date':merchant_data.get('create_date'),
                'write_date':merchant_data.get('write_date'),
            })
            merchant.sudo().write({
               'seq_code':merchant_data.get('seq_code')
            })
        supplier_merchant = request.env['ifs.gar.partner.supplier.merchant'].sudo().search([('merchant_id','=',merchant.id),('factor_supplier_id','=',factor_supplier.id)])
        if not supplier_merchant.exists():
            supplier_merchant = request.env['ifs.gar.partner.supplier.merchant'].sudo().create({
                'merchant_id':merchant.id,
                'factor_supplier_id':factor_supplier.id,
                'entry_id':invite_merchant.entry_id.id,
                't18_contract_info_id':invite_merchant.entry_id.t18_contract_info_id.id
            })
        factor_merchant = request.env['ifs.gar.partner.factor.merchant'].sudo().search([('merchant_id','=',merchant.id),('factor_id','=',factor.id)])
        if not factor_merchant.exists():
            factor_merchant = request.env['ifs.gar.partner.factor.merchant'].sudo().create({
               'merchant_id':merchant.id,
                'factor_id':factor.id,
            })
        merchant_data['factor_ids'] = [Command.link(factor.id)]
        merchant_data['supplier_ids'] = [Command.link(supplier.id)]
        merchant_data['ifs_company_id'] = base_company.id
        for loan_account_id in merchant_data.get('loan_account_ids'):
            loan_account_data = do_rpc(comm_var,'ifs.gar.loan.account',get_model_fields('ifs.gar.loan.account'),domain=[('id','=',loan_account_id)]).get('records')[0]
            loan_account = request.env['ifs.gar.loan.account'].sudo().search([('seq_code','=',loan_account_data.get('seq_code')),('factor_merchant_id','=',factor_merchant.id)])
            if not loan_account.exists():
                loan_account = request.env['ifs.gar.loan.account'].sudo().create({
                    'state':loan_account_data.get('state'),
                    'active':loan_account_data.get('active'),
                    'create_date':loan_account_data.get('create_date'),
                    'write_date':loan_account_data.get('write_date'),
                    'factor_merchant_id':factor_merchant.id
                })
                loan_account.sudo().write({
                   'seq_code':loan_account_data.get('seq_code')
                })
            for sub_loan_account_id in loan_account_data.get('sub_account_ids'):
                sub_loan_account_data = do_rpc(comm_var,'ifs.gar.sub.loan.account',get_model_fields('ifs.gar.sub.loan.account'),domain=[('id','=',sub_loan_account_id)]).get('records')[0]
                sub_loan_account = request.env['ifs.gar.sub.loan.account'].sudo().search([('seq_code','=',sub_loan_account_data.get('seq_code'))])
                if not sub_loan_account.exists():
                    sub_loan_account = request.env['ifs.gar.sub.loan.account'].sudo().create({
                       'state':sub_loan_account_data.get('state'),
                        'active':sub_loan_account_data.get('active'),
                        'approved_quota':sub_loan_account_data.get('approved_quota'),
                        'create_date':sub_loan_account_data.get('create_date'),
                        'write_date':sub_loan_account_data.get('write_date'),
                        'loan_account_id':loan_account.id,
                       'supplier_merchant_id':supplier_merchant.id
                    })
                    sub_loan_account.sudo().write({
                      'seq_code':sub_loan_account_data.get('seq_code')
                    }) 
    return invite_merchants.get('length')



def migrate_trade_order(limit=1,offset=0):
    comm_var = {}
    trade_definitions = do_rpc(comm_var,'ifs.gar.trade.definition',get_model_fields('ifs.gar.trade.definition')).get('records')
    for trade_definition in trade_definitions:
        definition = request.env['ifs.gar.trade.definition'].sudo().search([('name','=',trade_definition.get('name'))])
        if not definition.exists():
            definition = request.env['ifs.gar.trade.definition'].sudo().create(trade_definition)
    trade_order_fields =  get_model_fields('ifs.gar.trade.order')
    trade_order_fields = [item for item in trade_order_fields if not item.endswith('contract_info_id')] + ['order_info']
    trade_order_infos = do_rpc(comm_var,'ifs.gar.trade.order',['id'],domain=[],limit=limit,offset=offset)
    for trade_order_info in trade_order_infos.get('records'):
        trade_order_info = do_rpc(comm_var,'ifs.gar.trade.order',trade_order_fields,domain=[('id','=',trade_order_info.get('id'))]).get('records')[0]
        print(trade_order_info.get('seq_code'))
        trade_order = request.env['ifs.gar.trade.order'].sudo().search([('seq_code','=',trade_order_info.get('seq_code'))])
        if trade_order.exists():
            migrade_trade_order_contract(comm_var,trade_order_info, trade_order)
            continue
        if trade_order_info.get('order_info_definition_id'):
            trade_order_info['order_info_definition_id'] = request.env['ifs.gar.trade.definition'].sudo().search([('name','=',trade_order_info.get('order_info_definition_id')[1])]).id
        sub_loan_account = request.env['ifs.gar.sub.loan.account'].sudo().search([('seq_code','=',trade_order_info.get('sub_loan_account_id')[1])],limit=1)
        trade_order_info['sub_loan_account_id'] = sub_loan_account.id
        withdrawal_amount = trade_order_info.get('withdrawal_amount')
        trade_start_date = trade_order_info.get('trade_start_date')
        item_ids = trade_order_info.get('item_ids')
        plan_ids = trade_order_info.get('plan_ids')
        bill_id = trade_order_info.get('bill_id')
        order_bill_log_id = trade_order_info.get('bill_log_id')
        trade_order_info.pop('trade_start_date')
        trade_order_info.pop('withdrawal_amount')
        trade_order_info.pop('item_ids')
        trade_order_info.pop('plan_ids')
        trade_order_info['currency_id'] = sub_loan_account.merchant_id.currency_id.id
        trade_order_info.pop('bill_id')
        trade_order_info.pop('bill_log_id')
        
        trade_order = request.env['ifs.gar.trade.order'].sudo().create(trade_order_info)
        migrade_trade_order_contract(comm_var,trade_order_info, trade_order)
        bill = False
        order_bill_log = False
        for item_id in sorted(item_ids):
            item_data = do_rpc(comm_var,'ifs.gar.trade.order.item',['sequence','name','model','quantity','price','remark'],domain=[('id','=',item_id)]).get('records')[0]
            item_data['trade_order_id'] = trade_order.id
            request.env['ifs.gar.trade.order.item'].sudo().create(item_data)
        if bill_id:
            bill = request.env['ifs.gar.loan.account.bill'].sudo().search([('code','=',bill_id[1])])
            if not bill.exists():
                bill_data = do_rpc(comm_var,'ifs.gar.loan.account.bill',get_model_fields('ifs.gar.loan.account.bill'),domain=[('id','=',bill_id[0])]).get('records')[0]
                bill_data['currency_id'] = sub_loan_account.merchant_id.currency_id.id
                bill_data['sub_loan_account_id'] = sub_loan_account.id
                bill_log_ids = bill_data.get('bill_log_ids')
                bill_data.pop('bill_log_ids')
                bill = request.env['ifs.gar.loan.account.bill'].sudo().create(bill_data)
                for bill_log_id in sorted(bill_log_ids):
                    bill_log_data = do_rpc(comm_var,'ifs.gar.loan.account.bill.log',get_model_fields('ifs.gar.loan.account.bill.log'),domain=[('id','=',bill_log_id)]).get('records')[0]
                    bill_log = request.env['ifs.gar.loan.account.bill.log'].sudo().search([('bill_id','=',bill.id),('seq_code','=',bill_log_data.get('seq_code'))])
                    if not bill_log.exists():
                        if bill_log_data.get('prev_log_id'):
                            prev_log_data = do_rpc(comm_var,'ifs.gar.loan.account.bill.log',get_model_fields('ifs.gar.loan.account.bill.log'),domain=[('id','=',bill_log_data.get('prev_log_id')[0])]).get('records')[0]
                            prev_log = request.env['ifs.gar.loan.account.bill.log'].sudo().search([('bill_id','=',bill.id),('seq_code','=',prev_log_data.get('seq_code'))])
                            bill_log_data['prev_log_id'] = prev_log.id
                        bill_log_data['bill_id'] = bill.id
                        bill_log_data['order_id'] = 'ifs.gar.trade.order,%s' % trade_order.id
                        bill_log = request.env['ifs.gar.loan.account.bill.log'].sudo().create(bill_log_data)
        if order_bill_log_id:
            order_bill_log = request.env['ifs.gar.loan.account.bill.log'].sudo().search([('seq_code','=',order_bill_log_id[1])])
        
        order_plan_ids = []
        for plan_id in plan_ids:
            plan_data = do_rpc(comm_var,'ifs.gar.payment.plan',['id','payment_period','state','withdraw_state','repayment_date','payment_receipt','bill_id','bill_log_id','remark'],domain=[('id','=',plan_id)]).get('records')[0]
            plan_data['bill_id'] = bill.id if bill else False
            plan_data['bill_log_id'] = order_bill_log.id if order_bill_log else False
            plan_data['trade_order_id'] = trade_order.id
            plan = request.env['ifs.gar.payment.plan'].sudo().create(plan_data)
            order_plan_ids.append(plan.id)
        trade_order.sudo().write({
            'bill_id':bill.id if bill else False,
            'bill_log_id':order_bill_log.id if order_bill_log else False,
            'withdrawal_amount':withdrawal_amount,
            'trade_start_date':trade_start_date,
            'write_date':trade_order_info.get('write_date')
        })
    return trade_order_infos.get('length')

def migrate_lawfirm(limit,offset):
    invite_lawfirm_fields = get_model_fields('ifs.gar.invite.lawfirm')
    entry_lawfirm_fields = get_model_fields('ifs.gar.entry.lawfirm')
    lawfirm_fields = get_model_fields('ifs.partner.lawfirm')
    comm_var = {}
    invite_lawfirms = do_rpc(comm_var,'ifs.gar.invite.lawfirm',invite_lawfirm_fields,limit=limit,offset=offset)
    for invite_lawfirm_info in invite_lawfirms.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields + ['root_employee_id'],domain=[('id','=',invite_lawfirm_info.get('ifs_company_id')[0])]).get('records')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,invite_lawfirm_info.get('ifs_company_id')[0],base_company)
        migrate_company_hr(comm_var,company.get('company_registry'))
        factor = request.env['ifs.partner.factor'].sudo().search([('name','=',invite_lawfirm_info.get('factor_id')[1])])
        invite_lawfirm_info['ifs_company_id'] = base_company.id
        invite_lawfirm_info['factor_id'] = factor.id
        entry_ids = invite_lawfirm_info.get('entry_ids')
        lawfirm_id = invite_lawfirm_info.get('lawfirm_id')
        p10_contract_info_id = invite_lawfirm_info.get('p10_contract_info_id')
        invite_lawfirm_info.pop('entry_ids')
        invite_lawfirm_info.pop('lawfirm_id')
        invite_lawfirm_info.pop('p10_contract_info_id')
        invite_lawfirm = request.env['ifs.gar.invite.lawfirm'].sudo().search([('seq_code','=',invite_lawfirm_info.get('seq_code'))])
        if not invite_lawfirm.exists():
            invite_lawfirm = request.env['ifs.gar.invite.lawfirm'].sudo().create(invite_lawfirm_info)
        
        if p10_contract_info_id and not invite_lawfirm.p10_contract_info_id.exists():
            p10_contract_info = do_rpc(comm_var,'ifs.contract.info',get_model_fields('ifs.contract.info'),domain=[('id','=',p10_contract_info_id[0])]).get('records')[0]
            p10_contract_info.pop('partner_one')
            p10_contract_info.pop('partner_two')
            p10_contract_info.pop('template_id')
            p10_template = request.env['ifs.contract.template'].retrieve_by_code('P10', factor.id)
            p10_contract = request.env['ifs.contract.info'].sudo().create({
                'partner_one': '%s,%d' % (factor._name, factor.id),
                'partner_two': '%s,%d' % (invite_lawfirm._name, invite_lawfirm.id),
                'template_id': p10_template.id,
                **p10_contract_info
            })
            migrate_attachment(comm_var,p10_contract_info_id[0],p10_contract)
            invite_lawfirm.sudo().write({
                'p10_contract_info_id':p10_contract.id
            })
        
        for entry_id in sorted(entry_ids):
            entry_lawfirm_info = do_rpc(comm_var,'ifs.gar.entry.lawfirm',entry_lawfirm_fields,domain=[('id','=',entry_id)]).get('records')[0]
            entry_lawfirm = request.env['ifs.gar.entry.lawfirm'].sudo().search([('seq_code','=',entry_lawfirm_info.get('entry_lawfirm_info'))])
            if not entry_lawfirm.exists():
                entry_lawfirm_info['ifs_company_id'] = base_company.id
                entry_lawfirm_info['invite_id'] = invite_lawfirm.id
                if entry_lawfirm_info.get('last_entry_id'):
                    last_entry_info = do_rpc(comm_var,'ifs.gar.entry.lawfirm',entry_lawfirm_fields,domain=[('id','=',entry_lawfirm_info.get('last_entry_id')[0])]).get('records')[0]
                    last_entry = request.env['ifs.gar.entry.lawfirm'].sudo().search([('seq_code','=',last_entry_info.get('seq_code'))])
                    entry_lawfirm_info['last_entry_id'] = last_entry.id
                if entry_lawfirm_info.get('bank_id'):
                    entry_lawfirm_info['bank_id'] = request.env['res.bank'].sudo().search([('name','=',entry_lawfirm_info.get('bank_id')[1])]).id
                aaa = {k: v for k, v in entry_lawfirm_info.items() if k not in ['p10_contract_info_id', 'f42_contract_info_id', 'f43_contract_info_id']}
                entry_lawfirm = request.env['ifs.gar.entry.lawfirm'].sudo().create(aaa)
                migrate_entry_lawfirm_contract(comm_var,entry_lawfirm_info,entry_lawfirm)
        if not lawfirm_id:
            continue
        lawfirm_info = do_rpc(comm_var,'ifs.partner.lawfirm',get_model_fields('ifs.partner.lawfirm'),domain=[('id','=',lawfirm_id[0])]).get('records')[0]
        lawfirm = request.env['ifs.partner.lawfirm'].sudo().search([('seq_code','=',lawfirm_info.get('seq_code'))])
        if not lawfirm.exists():
            lawfirm = request.env['ifs.partner.lawfirm'].sudo().create({
                'ifs_company_id': base_company.id,
            })
        factor_lawfirm = request.env['ifs.gar.partner.factor.lawfirm'].sudo().search([('factor_id','=',factor.id),('lawfirm_id','=',lawfirm.id)])
        if not factor_lawfirm.exists():
            request.env['ifs.gar.partner.factor.lawfirm'].sudo().create({
                'entry_id': invite_lawfirm.entry_id.id,
                'factor_id': factor.id,
                'lawfirm_id':lawfirm.id,
                'p10_contract_info_id': invite_lawfirm.p10_contract_info_id.id,
                'f42_contract_info_id': invite_lawfirm.entry_id.f42_contract_info_id.id,
                'f43_contract_info_id': invite_lawfirm.entry_id.f43_contract_info_id.id,
            })
            idcard = request.env['hr.employee.idcard'].sudo(
                ).create_legal_from_entry(invite_lawfirm.entry_id)
            invite_lawfirm.entry_id.root_employee_id.sudo().write({
                'gender': idcard.gender,
                'birthday': idcard.birthday,
                'idcard_id': idcard.id,
            })
            invite_lawfirm.entry_id.sudo().write({
                'state': 'approval',
                'lawfirm_id': lawfirm.id,
            })
        
        print(base_company.name)
    return invite_lawfirms.get('length')


def migrate_insurance(limit=1,offset=0):
    comm_var = {}
    insurance_fields = get_model_fields('ifs.partner.insurance')
    insurances = do_rpc(comm_var,'ifs.partner.insurance',insurance_fields,limit=limit,offset=offset)
    for insurance_info in insurances.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields + ['root_employee_id'],domain=[('id','=',insurance_info.get('ifs_company_id')[0])]).get('records')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company_info = {
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            }
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration(base_company_info)
            migrate_base_company_doc(comm_var,insurance_info.get('ifs_company_id')[0],base_company)
        migrate_company_hr(comm_var,company.get('company_registry'))
        insurance = request.env['ifs.partner.insurance'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not insurance.exists():
            insurance_info['ifs_company_id'] = base_company.id
            insurance = request.env['ifs.partner.insurance'].sudo().create(insurance_info)
    return insurances.get('length')


        
def migrate_insurant(limit=1,offset=0):
    comm_var = {}
    insurant_fields = get_model_fields('ifs.partner.insurant')
    insurants = do_rpc(comm_var,'ifs.partner.insurant',insurant_fields,limit=limit,offset=offset)
    for insurant_info in insurants.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields,domain=[('id','=',insurant_info.get('ifs_company_id')[0])]).get('records')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration({
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            })
            for field in ['partner_id','doc_ids','finance_id','guarantor_employee_id','root_employee_id']:
                company.pop(field)
            base_company.sudo().write(company)
        migrate_base_company_doc(comm_var,insurant_info.get('ifs_company_id')[0],base_company)
        migrate_company_hr(comm_var,company.get('company_registry'))
        insurant = request.env['ifs.partner.insurant'].sudo().search([('ifs_company_id','=',base_company.id)])
        if not insurant.exists():
            insurant_info['ifs_company_id'] = base_company.id
            insurant = request.env['ifs.partner.insurant'].sudo().create(insurant_info)
    return insurants.get('length')


def migrate_channelsp(limit=1,offset=0):
    
    channelsp_fields = get_model_fields('ifs.partner.channelsp')
    comm_var = {}
    channelsps = do_rpc(comm_var,'ifs.partner.channelsp',channelsp_fields,limit=limit,offset=offset)
    for channelsp_info in channelsps.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields,domain=[('id','=',channelsp_info.get('ifs_company_id')[0])]).get('records')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration({
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            })
            for field in ['partner_id','doc_ids','finance_id','guarantor_employee_id','root_employee_id']:
                company.pop(field)
            base_company.sudo().write(company)
        migrate_base_company_doc(comm_var,channelsp_info.get('ifs_company_id')[0],base_company)
        migrate_company_hr(comm_var,company.get('company_registry'))
        channelsp = request.env['ifs.partner.channelsp'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not channelsp.exists():
            channelsp_info['ifs_company_id'] = base_company.id
            channelsp = request.env['ifs.partner.channelsp'].sudo().create(channelsp_info)
        insurant_channelsp_infos =  do_rpc(comm_var,'ifs.fli.partner.insurant.channelsp',['insurant_id','channelsp_id'],domain=[('channelsp_id','=',channelsp_info.get('id'))])
        for insurant_channelsp_info in insurant_channelsp_infos.get('records'):
            insurant_channelsp = request.env['ifs.fli.partner.insurant.channelsp'].sudo().search([('insurant_id.name','=',insurant_channelsp_info.get('insurant_id')[1]),('channelsp_id','=',channelsp.id)])
            if not insurant_channelsp.exists():
                insurant = request.env['ifs.partner.insurant'].sudo().search([('name','=',insurant_channelsp_info.get('insurant_id')[1])])
                insurant_channelsp = request.env['ifs.fli.partner.insurant.channelsp'].sudo().create({
                    'insurant_id': insurant.id,
                    'channelsp_id': channelsp.id,
                })
            
    return channelsps.get('length')


def migrate_insured(limit=1,offset=0):
    comm_var = {}
    insured_fields = get_model_fields('ifs.partner.insured')
    insureds = do_rpc(comm_var,'ifs.partner.insured',insured_fields + ['food_production_license_datas'],limit=limit,offset=offset)
    for insured_info in insureds.get('records'):
        company = do_rpc(comm_var,'ifs.base.company',base_company_fields + ['root_employee_id'],domain=[('id','=',insured_info.get('ifs_company_id')[0])]).get('records')[0]
        base_company = request.env['ifs.base.company'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not base_company.exists():
            base_company = request.env['ifs.base.company'].sudo().sync_business_registration({
                'name': company.get('name'),
                'email': company.get('email'),
                'phone': company.get('phone').replace(' ','').replace('+86','') if company.get('phone') else False,
                'company_registry': company.get('company_registry'),
                'street': company.get('street'),
                'business_address': company.get('business_address'),
                'logo': company.get('logo')
            })
            company.pop('partner_id')
            company.pop('doc_ids')
            company.pop('finance_id')
            company.pop('guarantor_employee_id')
            company.pop('root_employee_id')
            base_company.sudo().write(company)
            migrate_base_company_doc(comm_var,insured_info.get('ifs_company_id')[0],base_company)
            migrate_company_hr(comm_var,company.get('company_registry'))
        if insured_info.get('food_production_license_data_id'):
            food_production_license_data = request.env['galaxy.external.api.definition'].sudo().search([('name','=',insured_info.get('food_production_license_data_id')[1])])
            if not food_production_license_data.exists():
                food_production_license_data_info = do_rpc(comm_var,'galaxy.external.api.definition',['name','type','params_definition'],domain=[('name','=',insured_info.get('food_production_license_data_id')[1])])
                food_production_license_data = request.env['galaxy.external.api.definition'].sudo().create(food_production_license_data_info)
            insured_info['food_production_license_data_id'] = food_production_license_data.id
        insured = request.env['ifs.partner.insured'].sudo().search([('company_registry','=',company.get('company_registry'))])
        if not insured.exists():
            insured_info['ifs_company_id'] = base_company.id
            insured = request.env['ifs.partner.insured'].sudo().create(insured_info)
        insurant_insured_infos = do_rpc(comm_var,'ifs.fli.partner.insurant.insured',['insurant_id','insured_id','channelsp_id','insured_ifs_company_id'],domain=[('insured_id','=','ifs.partner.insured,%s' % (insured_info.get('id'))   )])
        for insurant_insured_info in insurant_insured_infos.get('records'):
            insurant_insured_info['insured_ifs_company_id'] = base_company.id
            insurant_insured_info['insured_id'] = 'ifs.partner.insured,%d' % (insured.id)
            insurant = request.env['ifs.partner.insurant'].sudo().search([('name','=',insurant_insured_info.get('insurant_id')[1])])
            insurant_insured_info['insurant_id'] = insurant.id
            insured_uniq_search_domain = [('insurant_id','=',insurant.id),('insured_ifs_company_id','=',base_company.id)]
            if insurant_insured_info.get('channelsp_id'):
                channelsp = request.env['ifs.partner.channelsp'].sudo().search([('name','=',insurant_insured_info.get('channelsp_id')[1])])
                insurant_insured_info['channelsp_id'] = channelsp.id
                insured_uniq_search_domain.append(('channelsp_id','=',channelsp.id))
            insurant_insured = request.env['ifs.fli.partner.insurant.insured'].sudo().search(insured_uniq_search_domain)
            if not insurant_insured.exists():
                insurant_insured = request.env['ifs.fli.partner.insurant.insured'].sudo().create(insurant_insured_info)
    return insureds.get('length')