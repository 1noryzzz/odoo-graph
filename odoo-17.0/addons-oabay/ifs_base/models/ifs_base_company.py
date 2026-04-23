# -*- coding: utf-8 -*-
import logging

from dateutil.relativedelta import relativedelta
from functools import reduce
from odoo import _, api, models, fields
from pypinyin import Style, lazy_pinyin
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class InclusiveFinancingBaseCompany(models.Model):
    _name = 'ifs.base.company'
    _inherit = [
        'mail.thread', 'mail.activity.mixin', 'galaxy.external.api.response.data.mixin', 'ifs.ir.sequence.mixin']
    _inherits = {'res.company': 'company_id'}
    _description = '金融业务的参与公司的基本信息'
    _order = 'name'

    @api.depends('name', 'company_registry')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.company_registry:
                name = record.company_registry + ' / ' + name
            res.append((record.id, name))
        return res

    company_id = fields.Many2one(
        'res.company', required=True, ondelete='restrict', auto_join=True, index=True,
        string='公司信息', copy=False)
    abbr = fields.Char(
        '公司名拼音首字母', compute='_compute_abbr', store=True, copy=False)
    org_auth_state = fields.Selection([
        ('unauthorized', '未认证'),
        ('certified', '已认证'),
    ], string='企业实名认证状态', default="unauthorized", copy=False)
    business_address = fields.Char(
        '营业地址', required=True, tracking=True, copy=False)
    doc_ids = fields.One2many(
        'ifs.base.company.doc', 'ifs_company_id', string='相关文件', copy=False)
    business_license = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='营业执照')
    charter = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='公司章程')
    deposit_license = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='开户许可证')
    
    company_code = fields.Char(
        '注册号', index=True, tracking=True, copy=False)  # companyCode
    business_date_from = fields.Datetime('执照有效期起', copy=False)
    business_date_to = fields.Datetime('执照有效期止', copy=False)
    capital = fields.Char('注册资本', copy=False)
    real_captical = fields.Char('实缴资本', copy=False)
    business_date = fields.Char(
        '执照有效期', compute='_compute_business_date', store=True, tracking=True)
    detail_ids = fields.One2many(
        'ifs.base.company.detail', 'ifs_company_id', string='详细信息', copy=False)
    key_person_ids = fields.One2many(
        'ifs.base.company.detail', 'ifs_company_id', string='主要人员', domain=[('code', '=', 'KEY_PERSON')])
    last_sync_time = fields.Datetime('最后一次同步数据的时间', tracking=True, copy=False)

    legal_name = fields.Char('法人姓名', related='legal_id.name')
    legal_phone = fields.Char('联系方式', related='legal_id.phone')
    legal_email = fields.Char('电子邮箱', related='legal_id.email')

    principal_name = fields.Char('负责人姓名', related='principal_id.name')

    finance_id = fields.Many2one(
        'res.partner', string='财务联系人', ondelete='restrict',
        domain="[('is_company', '=', False), '|', ('parent_id', '=', False), ('parent_id', '=', partner_id)]", copy=False)
    finance_name = fields.Char('财务联系人姓名', related='finance_id.name')
    finance_phone = fields.Char('联系电话', related='finance_id.phone')

    account_name = fields.Char(
        '账户名称', compute='_compute_account_info')
    account_no = fields.Char(
        '银行卡号', compute='_compute_account_info')
    deposit_bank = fields.Char(
        '开户行', compute='_compute_account_info')
    version = fields.Integer('version', copy=False)
    
    # 医疗机构特许经营相关
    practice_license = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='医疗机构执业许可证')
    practice_code = fields.Char(
        '医疗机构执业许可证登记号', index=True, tracking=True, copy=False)
    practice_definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='医疗机构执业许可证结果定义', domain=[('type', '=', 'response')], ondelete='restrict')
    practice_info = fields.Properties(
        '医疗机构执业许可证结果数据', definition='practice_definition_id.params_definition')
    practice_raw = fields.Json(
        compute='_compute_practice_raw', inverse='_inverse_practice_raw', string='医疗机构执业许可证结果源数据')
    business_type = fields.Selection(selection=[
        ('company','公司'),
        ('others','其他机构')
    ], string="组织类型", default="company")
    
    # 药品经营许可证相关
    trade_license = fields.Binary(
        compute='_compute_business_doc', inverse='_inverse_business_doc', string='药品经营许可证')
    trade_license_code = fields.Char(
        '药品经营许可证编号', index=True, tracking=True, copy=False)
    
    @api.depends('practice_info')
    def _compute_practice_raw(self):
        for record in self:
            if record.practice_info:
                record.practice_raw = record.practice_info

    def _inverse_practice_raw(self):
        for record in self:
            try:
                results = []
                if type(record.practice_raw) is dict:
                    for key, value in record.practice_raw.items():
                        results.append({
                            'name': key,
                            'value': value,
                        })
                    record.write({
                        'practice_info': results
                    })
            except:
                _logger.exception(f"parse practice_raw result {record.practice_raw} failed")

    @api.depends('name')
    def _compute_abbr(self):
        for record in self:
            if record.name:
                record.abbr = ''.join(list(map(lambda x: x.upper(), lazy_pinyin(
                    record.name, style=Style.FIRST_LETTER))))

    def _doc_mapping(self):
        return {
            'business_license': 'license',
            'charter': 'charter',
            'deposit_license': 'deposit_license',
            'practice_license': 'practice_license',
            'trade_license': 'trade_license',
        }

    @api.depends('doc_ids')
    def _compute_business_doc(self):
        for ifs_company in self:
            ifs_company.update(
                reduce(
                    lambda prev, curr: {
                        **prev,
                        reduce(
                            lambda a_key, c_item: c_item[0]
                            if c_item[1] == curr.name else a_key,
                            self._doc_mapping().items(), curr.name): curr.doc
                    } if curr.name in self._doc_mapping().values() else prev,
                    ifs_company.doc_ids,
                    reduce(
                        lambda po, k: {**po, k: False}, self._doc_mapping().keys(), {})
                )
            )

    def _inverse_business_doc(self):
        for ifs_company in self:
            for attr_key, doc_key in self._doc_mapping().items():
                if ifs_company[attr_key]:
                    self.env['ifs.base.company.doc'].update_doc(
                        ifs_company.id, doc_key, ifs_company[attr_key])

    @api.depends('business_date_from', 'business_date_to')
    def _compute_business_date(self):
        for record in self:
            if record.business_date_from:
                record.update({
                    'business_date': _('至').join([
                        fields.Date.to_string(record.business_date_from),
                        fields.Date.to_string(
                            record.business_date_to) if record.business_date_to else _(' 长期')
                    ])
                })

    def _need_sync(self, sync_frequency):
        self.ensure_one()
        if not self.last_sync_time:
            return True
        if sync_frequency == 'monthly':
            return self.last_sync_time < fields.Datetime.now() + relativedelta(months=-1)
        elif sync_frequency == 'weekly':
            return self.last_sync_time < fields.Datetime.now() + relativedelta(weeks=-1)
        elif sync_frequency == 'daily':
            return self.last_sync_time < fields.Datetime.now() + relativedelta(days=-1)
        else:
            return False

    @api.model
    def sync_business_registration(self, company_info):
        Config = self.env['ir.config_parameter'].sudo()
        registration_api_code = Config.get_param(
            'ifs_base.business_registration_api_code', 'TYC-QYJBXXJZYRY')
        sync_frequency = Config.get_param(
            'ifs_base.business_registration_update_frequency', 'monthly')

        ifs_base_company = self.search([
            '|',
            ('company_registry', '=', company_info.get('company_registry')),
            ('name', '=', company_info.get('name'))
        ])
        if not ifs_base_company.exists() or ifs_base_company._need_sync(sync_frequency):
            req = self.env['galaxy.external.api'].invoke(registration_api_code, query={
                'keyword': company_info.get('company_registry') or company_info.get('name'),
            })
            resp_data = req.retrieve_response('BUSINESS_INFO')
            
            if not resp_data.raw:
                raise UserError(_('根据传入的公司名称或社会统一信用代码未找到公司基本信息！'))

            address_resolve_data = self.env['galaxy.external.api'].invoke(
                'ADDRESS-RESOLVE', query={
                    'multimode': False, 'cleanTown': False,
                    'text': resp_data.raw.get('address'),
                }).retrieve_response('HQZNJXJG').raw
            province_id = self.env['res.country.state'].search(
                [('name', '=', address_resolve_data.get('province_name'))])
            city_id = self.env['res.country.area'].search(
                [('name', '=', address_resolve_data.get('city_name')),('state_id','=',province_id.id)])
            area_id = self.env['res.country.area'].search(
                [('name', '=', address_resolve_data.get('county_name')),('parent_area_id','=',city_id.id)])
            company_info.update({
                'name': resp_data.raw.get('name'),
                'company_registry': resp_data.raw.get('credit_no'),
                'business_address': resp_data.raw.get('address'),
                'state_id': province_id.id,
                'city': address_resolve_data.get('city_name'),
                'area_id': area_id.id,
                'street': address_resolve_data.get('address')
            })
            new_business_reg = {
                **company_info,
                'definition_id': resp_data.definition_id.id,
                'raw': resp_data.raw,
                'company_code': resp_data.raw.get('company_code'),
                'business_date_from': resp_data.raw.get('business_date_from'),
                'business_date_to': resp_data.raw.get('business_date_to'),
                'capital': resp_data.raw.get('capital'),
                'real_captical': resp_data.raw.get('real_captical'),
                'last_sync_time': fields.Datetime.now()
            }
            response_datas = req.response_ids.filtered(
                lambda x: x.code != 'BUSINESS_INFO')
            # KEY_PERSON 这是用来避免当前查询中，已经没有主要人员，但前面查询时有，这个时候需要删除
            clear_detail_codes = req.response_codes or response_datas.mapped(
                'code') + ['KEY_PERSON']
            # 添加新的详细信息，并删除旧的详细信息
            new_business_reg.update({
                'detail_ids': [fields.Command.create({
                    'code': rdata.code,
                    'definition_id': rdata.definition_id.id,
                    'raw': rdata.raw,
                }) for rdata in response_datas] + ([fields.Command.delete(
                    old_id) for old_id in ifs_base_company.detail_ids.filtered(
                        lambda x: x.code in clear_detail_codes).ids] if ifs_base_company.exists() else []),
            })

            if ifs_base_company.exists():
                ifs_base_company.write({
                    **new_business_reg,
                    'version': (ifs_base_company.version or 0) + 1,
                })
            else:
                exist_company = self.env['res.company'].search([
                    ('name', '=', new_business_reg.get('name'))], limit=1)
                if exist_company.exists():
                    new_business_reg.update({
                        'company_id': exist_company.id
                    })
                legal_person = self.env['res.partner'].create({
                    'name': resp_data.raw.get('legal_person'),
                })
                new_business_reg.update({
                    'legal_id': legal_person.id,
                    'principal_id': legal_person.id
                })
                ifs_base_company = self.create(new_business_reg)
                ifs_base_company.legal_id.write({
                    'parent_id': ifs_base_company.company_id.partner_id.id,
                })

                # 新建公司时，会自动把新建好的公司加到当前用户的“允许公司”中去，这里移除掉
                self.env.user.write({'company_ids': [fields.Command.unlink(
                    ifs_base_company.company_id.id)]})
        else:
            if company_info.get('email') and company_info.get('phone'):
                ifs_base_company.write({
                    'email': company_info.get('email'),
                    'phone': company_info.get('phone')
                })

        return ifs_base_company

    @api.depends('bank_ids')
    def _compute_account_info(self):
        for record in self:
            if record.bank_ids.exists():
                account = record.bank_ids[0]
                record.update({
                    'account_no': account.acc_number,
                    'account_name': account.partner_id.name,
                    'deposit_bank': account.bank_name,
                })
            else:
                record.update({
                    'account_name': record.partner_id.name if record.partner_id else '',
                    'deposit_bank': '',
                    'account_no': ''
                })

    # TODO: 对当前企业做实名认证，具体的实现由第三方扩展完成
    def certificate_company(self):
        self.ensure_one()
        self.org_auth_state = 'certified'


class InclusiveFinancingBaseCompanyDoc(models.Model):
    _name = 'ifs.base.company.doc'
    _description = '公司相关文件资料'
    _order = 'name, id'

    _sql_constraints = [
        ('same_ifs_company_id_doc_uniq',
         'unique (ifs_company_id, name)', '此资料已存在，请不要重复上传！')
    ]

    ifs_company_id = fields.Many2one(
        'ifs.base.company', string='公司信息', index=True, ondelete='cascade')
    name = fields.Selection([
        ('license', '营业执照'),
        ('charter', '公司章程'),
        ('deposit_license', '开户证可证'),
        ('practice_license', '医疗机构执业许可证'),
        ('trade_license', '药品经营许可证'),
    ], string='文件名称', required=True)

    doc = fields.Binary(required=True)

    def update_doc(self, ifs_company_id, name, doc):
        business_doc = self.search(
            [('ifs_company_id', '=', ifs_company_id), ('name', '=', name)])
        if business_doc.exists():
            business_doc.write({
                'doc': doc
            })
        else:
            self.create({
                'ifs_company_id': ifs_company_id,
                'name': name,
                'doc': doc,
            })


class InclusiveFinancingBaseCompanyDetail(models.Model):
    _name = 'ifs.base.company.detail'
    _inherit = ['galaxy.external.api.response.data.mixin']
    _description = '金融业务的参与公司的详细信息'
    _order = 'write_date desc'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', delegate=True, index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    code = fields.Char('结果标识')
