# -*- coding: utf-8 -*-


from odoo import _, api, models, fields, Command
from odoo.exceptions import MissingError


class InclusiveFinancingBaseCompanyRootUserWizard(models.AbstractModel):
    _name = 'ifs.base.company.root.user.wizard'
    _inherit = 'ifs.steps.wizard'
    _description = '公司根用户添加'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True,
        string='金融业务参与方', help='此保理方作为金融业务参与方，需要的资料信息')
    legal_id = fields.Many2one(
        'res.partner', related='ifs_company_id.legal_id', string='法人')
    name = fields.Char('员工姓名', required=True, related='legal_id.name')
    login = fields.Char(
        '用户名', required=True, related='ifs_company_id.seq_code')
    mobile_phone = fields.Char(
        '联系电话', required=True, related='legal_id.phone', readonly=False)
    emergency_phone = fields.Char('紧急联系电话')
    work_email = fields.Char(
        '工作电子邮箱', required=True, related='legal_id.email', readonly=False)
    work_position_ids = fields.Many2many(
        'ifs.work.position', string='职务', required=True)
    root_employee_id = fields.Many2one(
        'hr.employee', string='合作伙伴根用户', related='ifs_company_id.root_employee_id')
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别')
    notes = fields.Text('备注')

    can_change_contact = fields.Boolean(
        '可修改联系方式', compute='_compute_can_change_contact')

    @api.depends('root_employee_id', 'ifs_company_id', 'ifs_company_id.ifs_partners')
    def _compute_can_change_contact(self):
        for record in self:
            record.can_change_contact = not record.root_employee_id
            if len(record.ifs_company_id.ifs_partners or []) == 0:
                record.can_change_contact = True

    def action_confirm(self):
        user_info = self.sudo().read(
            ['name', 'login', 'mobile_phone', 'emergency_phone', 'work_email', 'gender', 'notes'])[0]
        
        ifs_company = self.env['ifs.base.company'].browse(self.ifs_company_id.id)
        if not ifs_company.legal_id:
            raise MissingError(_('数据错误，当前公司信息不完整，请联系管理员！'))

        # 注意这里需要跨公司获取职位，所以需要sudo
        default_wp = self.env['ifs.work.position'].sudo().search([
            ('company_id', '=', ifs_company.company_id.id),
            ('code', '=', 'SYSTEM')
        ], limit=1)
        
        user_info.pop('id')
        user_info.update({
            'state': 'normal',
            'company_id': self.ifs_company_id.company_id.id,
            'user_partner_id': self.legal_id.id,
            'is_root': True,
            'work_position_ids': [Command.link(default_wp.id)] if default_wp else False,
        })

        if self.root_employee_id:
            self.root_employee_id.sudo().write(user_info)
        else:
            self.ifs_company_id.root_employee_id = self.env['hr.employee'].sudo().create(
                user_info)
            # 写入Saleperson
            self.ifs_company_id.root_employee_id.sudo().user_partner_id.write({
                'user_id': self.env.user.id
            })
