# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingBaseCompany(models.Model):
    _inherit = 'ifs.base.company'

    # 下面是当前公司在系统中的角色，每一项最多只能有一个
    ifs_partner_factor_ids = fields.One2many(
        'ifs.partner.factor', 'ifs_company_id', string='保理方')
    ifs_partner_franchisee_ids = fields.One2many(
        'ifs.partner.franchisee', 'ifs_company_id', string='合伙人')
    ifs_partner_funder_ids = fields.One2many(
        'ifs.partner.funder', 'ifs_company_id', string='资金方')
    ifs_partner_lawfirm_ids = fields.One2many(
        'ifs.partner.lawfirm', 'ifs_company_id', string='律所')
    ifs_partner_merchant_ids = fields.One2many(
        'ifs.partner.merchant', 'ifs_company_id', string='采购方')
    ifs_partner_supplier_ids = fields.One2many(
        'ifs.partner.supplier', 'ifs_company_id', string='供应方')
    ifs_partner_insurance_ids = fields.One2many(
        'ifs.partner.insurance', 'ifs_company_id', string='保险公司')
    ifs_partner_insurant_ids = fields.One2many(
        'ifs.partner.insurant', 'ifs_company_id', string='投保人')
    ifs_partner_insured_ids = fields.One2many(
        'ifs.partner.insured', 'ifs_company_id', string='被保人')
    ifs_partner_channelsp_ids = fields.One2many(
        'ifs.partner.channelsp', 'ifs_company_id', string='服务商')

    factor_code = fields.Char(
        compute='_compute_factor_info', string='保理方编号')
    merchant_code = fields.Char(
        compute='_compute_merchant_info', string='采购方编号')
    supplier_code = fields.Char(
        compute='_compute_supplier_info', string='供应方编号')
    franchisee_code = fields.Char(
        compute='_compute_franchisee_info', string='合伙人编号')
    lawfirm_code = fields.Char(
        compute='_compute_lawfirm_info', string='律师事务所编号')
    funder_code = fields.Char(
        compute='_compute_funder_info', string='资金方编号')
    insurance_code = fields.Char(
        compute='_compute_insurance_info', string='保险公司编号')
    insurant_code = fields.Char(
        compute='_compute_insurant_info', string='投保人编号')
    insured_code = fields.Char(
        compute='_compute_insured_info', string='被保人编号')
    channelsp_code = fields.Char(
        compute='_compute_channelsp_info', string='服务商编号')

    @api.depends('ifs_partner_factor_ids')
    def _compute_factor_info(self):
        for record in self:
            factor_info = {'factor_code': False}
            if record.ifs_partner_factor_ids:
                factor_info.update({
                    'factor_code': record.ifs_partner_factor_ids[0].seq_code
                })
            record.update(factor_info)

    @api.depends('ifs_partner_merchant_ids')
    def _compute_merchant_info(self):
        for record in self:
            merchant_info = {'merchant_code': False}
            if record.ifs_partner_merchant_ids:
                merchant_info.update({
                    'merchant_code': record.ifs_partner_merchant_ids[0].seq_code
                })
            record.update(merchant_info)

    @api.depends('ifs_partner_supplier_ids')
    def _compute_supplier_info(self):
        for record in self:
            supplier_info = {'supplier_code': False}
            if record.ifs_partner_supplier_ids:
                supplier_info.update({
                    'supplier_code': record.ifs_partner_supplier_ids[0].seq_code
                })
            record.update(supplier_info)
            
    @api.depends('ifs_partner_franchisee_ids')
    def _compute_franchisee_info(self):
        for record in self:
            franchisee_info = {'franchisee_code': False}
            if record.ifs_partner_franchisee_ids:
                franchisee_info.update({
                    'franchisee_code': record.ifs_partner_franchisee_ids[0].seq_code
                })
            record.update(franchisee_info)

    @api.depends('ifs_partner_lawfirm_ids')
    def _compute_lawfirm_info(self):
        for record in self:
            lawfirm_info = {'lawfirm_code': False}
            if record.ifs_partner_lawfirm_ids:
                lawfirm_info.update({
                    'lawfirm_code': record.ifs_partner_lawfirm_ids[0].seq_code
                })
            record.update(lawfirm_info)
            
    @api.depends('ifs_partner_funder_ids')
    def _compute_funder_info(self):
        for record in self:
            funder_info = {'funder_code': False}
            if record.ifs_partner_funder_ids:
                funder_info.update({
                    'funder_code': record.ifs_partner_funder_ids[0].seq_code
                })
            record.update(funder_info)
            
    @api.depends('ifs_partner_insurance_ids')
    def _compute_insurance_info(self):
        for record in self:
            insurance_info = {'insurance_code': False}
            if record.ifs_partner_insurance_ids:
                insurance_info.update({
                    'insurance_code': record.ifs_partner_insurance_ids[0].seq_code
                })
            record.update(insurance_info)
            
    @api.depends('ifs_partner_insurant_ids')
    def _compute_insurant_info(self):
        for record in self:
            insurant_info = {'insurant_code': False}
            if record.ifs_partner_insurant_ids:
                insurant_info.update({
                    'insurant_code': record.ifs_partner_insurant_ids[0].seq_code
                })
            record.update(insurant_info)
            
    @api.depends('ifs_partner_insured_ids')
    def _compute_insured_info(self):
        for record in self:
            insured_info = {'insured_code': False}
            if record.ifs_partner_insured_ids:
                insured_info.update({
                    'insured_code': record.ifs_partner_insured_ids[0].seq_code
                })
            record.update(insured_info)
            
    @api.depends('ifs_partner_channelsp_ids')
    def _compute_channelsp_info(self):
        for record in self:
            channelsp_info = {'channelsp_code': False}
            if record.ifs_partner_channelsp_ids:
                channelsp_info.update({
                    'channelsp_code': record.ifs_partner_channelsp_ids[0].seq_code
                })
            record.update(channelsp_info)

    # 激活当前公司的金融业务身份
    def active_ifs_partner(self, ifs_partner):
        self.ensure_one()
        ifs_partners = (self.company_id.ifs_partners or [])
        if ifs_partner not in ifs_partners:
            self.company_id.write({
                'ifs_partners': ifs_partners + [ifs_partner]
            })

    def inactive_ifs_partner(self, ifs_partner):
        self.ensure_one()
        self.company_id.write({
            'ifs_partners': [pt for pt in (self.company_id.ifs_partners or []) if pt != ifs_partner]
        })
        if not self.company_id.ifs_partners or len(self.company_id.ifs_partners) == 0:
            self.detail_ids.unlink()
            self.unlink()

    def view_ifs_company(self):
        ifs_company = self.search(
            [('company_id', '=', self.env.company.id)], limit=1)
        if ifs_company.exists() and self.env.company.ifs_partners:
            return {
                'name': '公司信息',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'ifs.base.company',
                'view_id': self.env.ref('ifs_partner.ifs_base_company_view_form_my').id,
                'res_id': ifs_company.id if ifs_company.exists() else False,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': '公司信息',
                'view_mode': 'form',
                'res_model': 'res.company',
                'res_id': self.env.company.id,
                'target': 'current',
                'context': {
                    'form_view_initial_mode': 'edit',
                },
            }

    def action_create_business_license(self):
        # TODO: 这里是更新当前登录企业的营业执照，需要另外写一个向导，需要走审核流程
        pass
        # return {
        #     'name': _('更新营业执照'),
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'ifs.partner.factor.business.license.wizard',
        #     'target': 'new',
        #     'context': {
        #         'default_ifs_company_id': self.ifs_company_id.id,
        #         'res_model': 'ifs.partner.factor.business.license.wizard',
        #         'next_model': 'ifs.partner.factor.bank.wizard',
        #     }
        # }

    def action_update_account(self):
        # TODO: 这里是更新当前登录企业的营业执照，需要另外写一个向导，需要走审核流程
        pass
        # return {
        #     'name': _('更新银行账户'),
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'ifs.partner.factor.bank.wizard',
        #     'target': 'new',
        #     'context': {
        #         'default_ifs_company_id': self.ifs_company_id.id,
        #     }
        # }
