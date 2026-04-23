# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied

# FRANCHISEETYPE=[
#         ('business', '事业合伙人'),
#         ('agent', '代理事业合伙人'),
#     ]
class GuaranteeAccountsRecInviteFranchisee(models.Model):
    _name = 'ifs.gar.invite.franchisee'
    _inherit = ['ifs.gar.invite.mixin']
    _description = '邀请合伙人进件'
    _order = 'create_date desc'
    _invite_ifs_partner = 'franchisee'

    _sql_constraints = [
        ('factor_franchisee_no_uniq', 'unique (factor_id, ifs_company_id)', '此合伙人已经邀请过了！')
    ]

    factor_id = fields.Many2one(
        'ifs.partner.factor', required=True,
        string='保理方', index=True, ondelete='restrict', copy=False)
    state = fields.Selection([
        ('draft', '草稿'),
        ('sended', '已发邀请'),
        ('waiting', '待提交'),
        ('activation', '待开通'),
        ('ready', '已开通'),
    ], string='状态', default='draft')
    
    can_send = fields.Boolean('可重发邀请信', compute="_compute_can_send")
    
    @api.depends('state')
    def _compute_can_send(self):
        for record in self:
            record.can_send = (
                record.factor_id.company_id.id == self.env.company.id and record.state in ['draft', 'sended'])

    # company_name = fields.Char('公司名称')
    # franchisee_type = fields.Selection(FRANCHISEETYPE, string='事业合伙人类型')
    # invite_franchisee_type = fields.Char(string='事业合伙人类型', compute='_compute_invite_franchisee_type', readonly=False)
    # area_id = fields.Many2one("res.country.area", string='市', ondelete='restrict',
    #                           domain="[('state_id', '=?', state_id), ('area_type', 'in', ['dc', 'city'])]")
    # state_id = fields.Many2one("res.country.state", string='省',
    #                            ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    # country_id = fields.Many2one('res.country', string='国家', ondelete='restrict',
    #                              default=lambda self: self.env.user.company_id.country_id)
    # area_nature = fields.Selection([
    #     ('share', '主要区域'),
    #     ('exclusion', '排他区域'),
    # ], string='区域性质')
    # currency_id = fields.Many2one(
    #     'res.currency', default=lambda self: self.env.user.company_id.currency_id, required=True)
    # area_agency_fee = fields.Monetary('区域代理费')
    # first_year_base_service_fee = fields.Percent('基础服务费(首年收益)')
    # first_year_trade_service_fee = fields.Percent('交易服务费(首年收益)')
    # follow_up_base_service_fee = fields.Percent('基础服务费(后续收益)')
    # follow_up_trade_service_fee = fields.Percent('交易服务费(后续收益)')
    
    # @api.depends('franchisee_type')
    # def _compute_invite_franchisee_type(self):
    #     self.invite_franchisee_type = self.franchisee_type

    # @api.onchange('franchisee_type')
    # def _onchange_franchisee_info(self):
    #     if self.franchisee_type == 'business':
    #         self.write({
    #             'area_nature': 'share',
    #             'first_year_base_service_fee': 50.0,
    #             'first_year_trade_service_fee': 40.0,
    #             'follow_up_base_service_fee': 15.0,
    #             'follow_up_trade_service_fee': 15.0
    #         })
    #     else:
    #         self.write({
    #             'area_nature': 'exclusion',
    #             'first_year_base_service_fee': 60.0,
    #             'first_year_trade_service_fee': 50.0,
    #             'follow_up_base_service_fee': 20.0,
    #             'follow_up_trade_service_fee': 20.0
    #         })

    # def _check_invited(self, business_id):
    #     invited = self.search([
    #         ('business_id', '=', business_id.id),
    #         ('factor_id', '=', self.factor_id.id)
    #     ])
    #     if invited.exists():
    #         if invited.state == 'ready':
    #             raise UserError(_('此事业合伙人已开通！'))
    #         else:
    #             raise UserError(_('您已邀请过此事业合伙人！'))

    #     return False

    # @api.model
    # def create(self, vals):
    #     if self.env.company.ifs_partner != 'factor':
    #         raise UserError(_('保理方才可以使用事业合伙人邀请功能！'))
    #     vals['sales_user_id'] = self.env.user.id
    #     vals['franchisee_type'] = vals['invite_franchisee_type']
    #     return super(GuaranteeAccountsRecInviteFranchisee, self).create(vals)

    def start_invite(self):
        if 'factor' in (self.env.company.ifs_partners or []):
            factor = self.env['ifs.partner.factor'].search([
                ('company_id', '=', self.env.company.id)
            ])
            if not factor.exists():
                raise AccessDenied(_('当前保理方数据异常，请联系管理员！'))
            return {
                'name': _('邀请合伙人向导'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.invite.franchisee.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_factor_id': factor.id,
                }
            }
        else:
            raise AccessDenied(_('请切换到可发送邀请的公司'))
    
    def action_reinvite(self):
        if self.can_send:
            return {
                'name': _('添加联系人信息'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[False, 'form']],
                'res_model': 'ifs.gar.invite.franchisee.root.user.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'default_ifs_company_id': self.ifs_company_id.id,
                }
            }
