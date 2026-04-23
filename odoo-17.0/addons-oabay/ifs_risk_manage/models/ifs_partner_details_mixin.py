# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingPartnerDetailMixin(models.AbstractModel):
    _name = 'ifs.partner.details.mixin'
    _description = '各参与方相关的公司情况'

    history_legal_person_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='历史法人')
    history_stock_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='历史股东')
    history_staffer_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='历史董监高')
    main_supplier_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业供应商')
    main_customers_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业客户')
    taxpayer_type_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='纳税人类型')
    judicial_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='司法协助')
    executee_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='被执行人')
    dishonest_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='失信被执行人')
    judgment_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='判决文书')
    weibo_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业微博')
    wechat_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业微信公众号')
    certificate_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业资质')
    punishment_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='行政处罚')
    abnormal_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='异常名录')
    mortgage_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='抵押登记')
    trademark_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业商标信息')
    patent_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='企业专利信息')
    software_copyright_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='软件著作权')
    copyright_ids = fields.One2many(
      'ifs.base.company.detail', compute='_compute_partner_details_ids', string='作品著作权')
    website_ids = fields.One2many(
        'ifs.base.company.detail', compute='_compute_partner_details_ids', string='网站备案')
    left_arch_category_ids = fields.One2many(
        'ifs.base.company.category', compute='_compute_arch_category', string='企业架构(左)')
    right_arch_category_ids = fields.One2many(
        'ifs.base.company.category', compute='_compute_arch_category', string='企业架构(右)')
    top_arch_category_ids = fields.One2many(
        'ifs.base.company.category', compute='_compute_arch_category', string='企业架构(上)')
    bottom_arch_category_ids = fields.One2many(
        'ifs.base.company.category', compute='_compute_arch_category', string='企业架构(下)')
    
    @api.depends('detail_ids')
    def _compute_arch_category(self):
        for record in self:
            category_ids = self.env['ifs.base.company.category'].search([
            ])
            record.update({
                'left_arch_category_ids': category_ids.filtered(lambda x: x.orient == 'left'),
                'right_arch_category_ids': category_ids.filtered(lambda x: x.orient == 'right'),
                'top_arch_category_ids': category_ids.filtered(lambda x: x.orient == 'top'),
                'bottom_arch_category_ids': category_ids.filtered(lambda x: x.orient == 'bottom')
            })

    @api.depends('detail_ids')
    def _compute_partner_details_ids(self):
        detail_ids = {
            'history_legal_person_ids': 'PAST-LEGALPERSON',
            'history_stock_ids': 'PAST-HOLDER',
            'history_staffer_ids': 'PAST-STAFFER',
            'main_supplier_ids': 'HQQYGYSXX',
            'main_customers_ids': 'HQQYKHXX',
            'taxpayer_type_ids': 'HQQYNSRXX',
            'judicial_ids': 'HQQYSFXZXX',
            'executee_ids': 'HQQYBZXRXX',
            'dishonest_ids': 'HQQYSXBZXRXX',
            'judgment_ids': 'HQQYPJWSXX',
            'weibo_ids': 'HQQYWBXX',
            'wechat_ids': 'HQQYWXGZH',
            'certificate_ids': 'HQQYZZZS',
            'punishment_ids': 'HQQYXZCFXX',
            'abnormal_ids': 'HQQYYCMLXX',
            'mortgage_ids': 'HQQYDYDJXX',
            'trademark_ids': 'HQQYSBXX',
            'patent_ids': 'HQQYZLXX',
            'software_copyright_ids': 'HQQYRJZZQXX',
            'copyright_ids': 'HQQYZPZZQXX',
            'website_ids': 'HQQYWZBAXX',
        }
        for key,value in detail_ids.items():
            self._detail_ids(key, value)
        
    def _detail_ids(self, field, code):
        for record in self:
            record[field] = False
            if record.detail_ids:
                record[field] = record.detail_ids.filtered(
                    lambda r: r.code == code)
