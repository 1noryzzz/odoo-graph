# -*- coding: utf-8 -*-


from odoo import _, api, fields, models
from random import randint


class InclusiveFinancingWorkPosition(models.Model):
    _name = "ifs.work.position"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '普惠金融场景下的员工职位管理'

    _sql_constraints = [
        ('same_company_work_position_name_uniq',
         'unique (company_id, name)', '您输入的职位名称已存在！'),
        ('same_company_work_position_code_uniq',
         'unique (company_id, code)', '您输入的职位编辑已存在！')
    ]

    def _get_default_color(self):
        return randint(1, 11)

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'company_id' in defaults and 'category_ids' in fields_list:
            defaults.setdefault('category_ids', [self.env.ref(
                'ifs_base.module_category_ifs_base').id])

        return defaults

    name = fields.Char('职位名称', required=True, tracking=True)
    code = fields.Char('职位编码', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', required=True, ondelete='restrict', auto_join=True, index=True,
        string='所属公司', help='设立此职位的公司', default=lambda self: self.env.company.id)
    category_ids = fields.Many2many(
        'ir.module.category', string='职位类别', compute='_compute_category_ids')
    color = fields.Integer('标签颜色', default=_get_default_color)
    groups_id = fields.Many2many(
        'res.groups', string='Groups', domain="[('category_id', 'in', category_ids)]", tracking=True)
    wechat_tag_ids = fields.Many2many(
        'wechat.offiaccount.taglist', 'ifs_work_position_tag_rel',
        'position_id', 'tag_id', string='微信公众号用户标签', tracking=True)
    need_one_time_passwd = fields.Boolean(
        '是否需要动态令牌', default=False, tracking=True)

    @api.depends('company_id')
    def _compute_category_ids(self):
        for record in self:
            record.category_ids = [self.env.ref(
                'ifs_base.module_category_ifs_base').id]

    def write(self, vals):
        res = super(InclusiveFinancingWorkPosition, self).write(vals)

        # 因为更新了职位设定，这里需要刷新一下相应的员工权限
        if 'groups_id' in vals:
            emps = self.env['hr.employee'].search(
                [('work_position_ids', '=', self.id), ('company_id', '=', self.company_id.id)])
            for emp in emps:
                emp.sudo().user_id.with_context(mail_notrack=True).write({
                    'groups_id': [fields.Command.set(emp.work_position_ids.groups_id.ids)],
                })

        return res
