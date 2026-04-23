# -*- coding: utf-8 -*-


from odoo import _, api, models, fields


class InclusiveFinancingBaseCompanyShareHolder(models.Model):
    _name = 'ifs.base.company.shareholder'
    _description = '金融业务的参与公司的股东信息'
    _order = 'ifs_company_id, shareholder_id'
    _rec_name = 'name'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', string='参与公司', required=True, ondelete='cascade')
    shareholder_id = fields.Many2one(
        'res.partner', string='股东', required=True, ondelete='restrict')
    name = fields.Char('股东名称', related='shareholder_id.name')
    subscribed_ratio = fields.Percent('认缴占比', digits=(16, 2), required=True)
    paid_in_ratio = fields.Percent('实缴占比', digits=(16, 2), required=True)
    share_type = fields.Selection([
        ('common', '普通股'),
        ('preferred', '优先股'),
    ], string='股份类型', default='common', required=True)
    share_type_other = fields.Char('其他股份类型')
    paid_in_capital = fields.Char('实缴资本')
    subscribed_capital = fields.Char('认缴资本')
    type = fields.Selection([('1','公司'),('2','个人'),('3','其他')],string="股东类型")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' in vals:
                partner = self.env['res.partner'].search([
                    ('name', '=', vals['name']),
                ])
                if not partner.exists():
                    partner = self.env['res.partner'].create({
                        'name': vals['name'],
                        'is_company': False,
                    })
                if partner and len(partner) > 1:
                    partner = partner[0]
                vals['shareholder_id'] = partner.id

        super().create(vals_list)

    def fetch_shareholder_data(self, model=False, model_id=False):
        if self.shareholder_id.is_company == True:
            ifs_company = self.env['ifs.base.company'].search(
                [('partner_id', '=', self.shareholder_id.id)])
            ifs_company._compute_shareholder_ids()
            return [{
                'id': shareholder.id,
                'name': shareholder.name,
                # 'lineContent': stock_info.lineContent
            } for shareholder in ifs_company.shareholder_ids] if ifs_company.shareholder_ids else []
        else:
            pass
