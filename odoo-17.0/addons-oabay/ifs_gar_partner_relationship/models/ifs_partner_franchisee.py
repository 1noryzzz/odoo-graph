# -*- coding: utf-8 -*-

from odoo import _, api, models, fields

INDUSTRY = [
    ('farming_and_forestry', '农林牧渔'),
    ('medical_science', '医药卫生'),
    ('building_materials', '建筑建材'),
    ('water_power', '水利水电'),
    ('transportation', '交通运输'),
    ('IT_industry', '信息产业'),
    ('clothing_textile', '服装纺织'),
    ('food_and_catering', '食品餐饮'),
    ('finance', '金融'),
    ('professional_services', '专业服务'),
]


class InclusiveFinancingPartnerFranchisee(models.Model):
    _inherit = 'ifs.partner.franchisee'

    factor_ids = fields.One2many(
        'ifs.gar.partner.factor.franchisee', 'franchisee_id', string='与保理方的合作关系')
    industry = fields.Char('从事行业')
    industry_selection = fields.Selection(INDUSTRY, string='从事行业', store=False)
    industry_time = fields.Char('从业年限')
    industry_resources = fields.Selection([
        ('highlymatch', '高度匹配'),
        ('diggable', '可挖掘'),
        ('general', '一般'),
    ], string='行业资源')
    franchisee_suggest = fields.Text('建议与意见')
    family_address = fields.Char('家庭地址', tracking=True)

    def get_industry(self):
        return [industry for industry in INDUSTRY]

    # @override from current.company.partner.mixin
    # def _compute_partner_related(self):
    #     for record in self:
    #         record.partner_related = ''
    #         if self.env.company.ifs_partner == 'factor':
    #             if record.factor_ids.filtered(
    #                     lambda factor_franchisee: factor_franchisee.factor_id.business_id.company_id.id == self.env.company.id).exists():
    #                 record.partner_related = 'factor-franchisee'

    # def _create_or_update_relationship(self, franchisee, vals):
    #     if self.env.company.ifs_partner == 'factor':
    #         inner_vals = {}
    #         for k, v in vals.items():
    #             if k in self.env['ifs.gar.partner.factor.franchisee']._fields:
    #                 inner_vals[k] = v

    #         is_exist = False
    #         factor_franchisee = False
    #         if franchisee.factor_ids.exists():
    #             factor_franchisee = franchisee.factor_ids.filtered(
    #                 lambda factor_franchisee: factor_franchisee.factor_id.business_id.company_id.id == self.env.company.id)
    #             if factor_franchisee.exists():
    #                 factor_franchisee.write(inner_vals)
    #                 is_exist = True

    #         factor = self.env['ifs.partner.factor'].search(
    #             [('business_id.company_id', '=', self.env.company.id)])
    #         if not is_exist and factor.exists():
    #             inner_vals.update({
    #                 'factor_id': factor.id,
    #                 'franchisee_id': franchisee.id,
    #             })
    #             factor_franchisee = self.env['ifs.gar.partner.factor.franchisee'].create(
    #                 inner_vals)

    # @api.model
    # def create(self, vals):
    #     franchisee = super().create(vals)
    #     self._create_or_update_relationship(franchisee, vals)
    #     return franchisee

    # def write(self, vals):
    #     rst = super().write(vals)
    #     self._create_or_update_relationship(self, vals)
    #     return rst
