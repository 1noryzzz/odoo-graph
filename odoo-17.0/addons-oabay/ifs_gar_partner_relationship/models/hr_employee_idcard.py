# -*- coding: utf-8 -*-


from odoo import _, models, fields


class EmployeeIDcard(models.Model):
    _inherit = 'hr.employee.idcard'

    household_register = fields.Image('户口本复印件', groups="hr.group_hr_user")
