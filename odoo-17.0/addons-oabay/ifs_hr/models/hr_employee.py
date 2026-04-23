# -*- coding: utf-8 -*-


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.addons.phone_validation.tools import phone_validation


class InclusiveFinanchingHrEmployee(models.Model):
    _inherit = ['hr.employee']

    name = fields.Char('员工姓名')
    login = fields.Char(
        '用户名', related='user_id.login', readonly=False, required=True, index=True)
    mobile_phone = fields.Char('联系电话', tracking=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('paused', '停用'),
        ('normal', '正常')
    ], string='状态', required=True, default="normal", tracking=True)
    work_position_ids = fields.Many2many(
        'ifs.work.position', string='职务', domain="[('company_id', '=', company_id)]", required=True, tracking=True)
    otp_auth_id = fields.Many2one(
        'otp.authentication', ondelete='restrict', string='动态令牌', tracking=True,
        domain=lambda self: [('state', '=', 'normal'), ('company_id', '=', self.env.company.id)])
    is_need_otp = fields.Boolean(
        compute='_compute_is_need_otp', string='是否需要动态令牌')

    idcard_id = fields.Many2one(
        'hr.employee.idcard', string='身份证信息', tracking=True)
    identification_id = fields.Char(
        '身份证号码', groups="hr.group_hr_user", related='idcard_id.idcard_no', store=True, tracking=True)
    nationality = fields.Char('民族', related='idcard_id.nationality')
    idcard_address = fields.Char(
        '身份证地址', related='idcard_id.address')
    authority = fields.Char(
        '签发机关', related='idcard_id.authority')
    start_date = fields.Date(
        '起始日期', related='idcard_id.start_date')
    end_date = fields.Date(
        '失效日期', related='idcard_id.end_date')
    idcard_expiry_date = fields.Char(
        compute='_compute_idcard_expiry_date', string='身份证有效期')
    front_image = fields.Image(
        related='idcard_id.front_image', string='身份证人像面')
    back_image = fields.Image(
        related='idcard_id.back_image', string='身份证国徽面')

    def _is_super_admin(self):
        return self.env.ref('base.group_system').id in self.user_id.groups_id.ids

    @api.depends('work_position_ids')
    def _compute_is_need_otp(self):
        for record in self:
            if record.work_position_ids and record.work_position_ids.filtered(lambda wp: wp.need_one_time_passwd).exists():
                record.is_need_otp = True
            else:
                record.is_need_otp = False

    @api.depends('start_date', 'end_date')
    def _compute_idcard_expiry_date(self):
        for emp in self:
            emp.idcard_expiry_date = ''
            if emp.start_date:
                emp.idcard_expiry_date = _('至').join([
                    fields.Date.to_string(emp.start_date),
                    fields.Date.to_string(
                        emp.end_date) if emp.end_date else _(' 长期')
                ])

    @api.onchange('mobile_phone')
    def _mobile_simply_validate(self):
        if self.mobile_phone:
            try:
                country = self.env.company.country_id
                phone_validation.phone_parse(
                    self.mobile_phone,
                    country.code if country else None)
            except:
                raise ValidationError(_("请正确输入手机号"))

    # @api.constrains('mobile_phone')
    # def _check_mobile_phone(self):
    #     for record in self:
    #         if record.mobile_phone:
    #             mobile_count = self.search_count(
    #                 [('mobile_phone', '=', record.mobile_phone), ('active', '=', True)])
    #             if mobile_count > 1:
    #                 raise ValidationError(_("手机号已存在！"))

    @api.model
    def create(self, vals):
        if 'company_id' not in vals:
            vals['company_id'] = self.env.company.id

        user_exist = 'user_id' in vals
        if not user_exist:
            vals.update({
                'user_id': self.env['res.users'].signup_from_inclusive_financing(vals).id,
            })
        employee = super().create(vals)

        if not user_exist:
            employee.user_id.with_context(mail_notrack=True).write({
                'parent_id': employee.company_id.partner_id.id,
                'groups_id': [fields.Command.set(employee.work_position_ids.groups_id.ids)],
            })

        return employee

    def write(self, vals):
        employee = super().write(vals)

        if 'mobile_phone' in vals:
            # 修改手机号操作，用修改登录用户
            self.sudo().user_id.with_context(mail_notrack=True).write({
                'phone': self.mobile_phone,
                'mobile': self.mobile_phone,
            })

        if 'name' in vals:
            self.user_partner_id.write({
                'name': vals.get('name')
            })

        if 'work_position_ids' in vals and not self._is_super_admin():
            self.sudo().user_id.with_context(mail_notrack=True).write({
                'groups_id': [fields.Command.set(self.work_position_ids.groups_id.ids)],
            })

        return employee

    # 删除
    def unlink(self):
        if self._is_super_admin():
            raise UserError(_("超级管理员不可以删除"))

        # 将员工设置为不可见,并清空其对应职位
        res = self.write({
            'active': False,
            'work_position_ids': [fields.Command.clear()]
        })

        self.user_id.with_context(mail_notrack=True).write({
            'groups_id': [fields.Command.set([self.env.ref('base.group_public').id])]
        })

        return res

    def action_open_idcard_uploader(self):
        self.ensure_one()
        return {
            'name': _('身份证上传'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ifs.hr.idcard.uploader',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            }
        }

    def update_state_to_normal(self):
        if self._is_super_admin():
            raise UserError(_("不能操作超级管理员"))

        self.write({
            'state': 'normal'
        })

        self.user_id.with_context(mail_notrack=True).write({
            'groups_id': [fields.Command.set(self.work_position_ids.groups_id.ids)]
        })

    def update_state_to_paused(self):
        if self._is_super_admin():
            raise UserError(_("超级管理员不能停用"))

        if self.env.uid == self.user_id.id:
            raise UserError(_("不能停用自己"))

        self.write({
            'state': 'paused'
        })

        self.user_id.with_context(mail_notrack=True).write({
            'groups_id': [fields.Command.set([self.env.ref('base.group_public').id])]
        })

    @api.model
    def is_need_one_time_passwd(self, user_id):
        if self.env['ir.config_parameter'].sudo().get_param('ifs.hr.otp.global.activated', False):
            query_employee = self.search(
                [('user_id', '=', user_id), ('work_position_ids.need_one_time_passwd', '=', True)], limit=1)
            if query_employee.exists():
                return query_employee.otp_auth_id

        return False
