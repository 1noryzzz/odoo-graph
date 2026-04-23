# -*- coding: utf-8 -*-

import re

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime


IDCARD_REGEX = '[1-9][0-9]{14}([0-9]{2}[0-9X])?'


class EmployeeIDcard(models.Model):
    '''
    这里单独把身份证信息存在这里，是便于一张身份证对应多个公司的员工
    因为某一个公司的员工离职后，身份证信息还是要保留的，他可能会入职其他公司
    '''
    _name = 'hr.employee.idcard'
    _description = '身份证信息'

    _sql_constraints = [
        ('idcard_no_uniq', 'unique (idcard_no)', '身份证号已存在！')
    ]

    def name_get(self):
        res = []
        for idcard in self:
            res.append((idcard.id, f'{idcard.name} ({idcard.idcard_no})'))
        return res

    employee_ids = fields.One2many('hr.employee', 'idcard_id', string='关联员工')
    name = fields.Char('姓名', required=True)
    idcard_no = fields.Char(
        '身份证号', required=True, index=True, groups="hr.group_hr_user")
    nationality = fields.Char('民族')
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '未知')
    ], groups="hr.group_hr_user", default='other', string='性别')
    birthday = fields.Date('出生日期', compute='_compute_birthday', store=True)
    address = fields.Char('证件地址')
    authority = fields.Char('签发机关', required=True)
    start_date = fields.Date('起始日期', required=True)
    end_date = fields.Date('失效日期')
    front_image = fields.Image(
        '身份证人像面', required=True, groups="hr.group_hr_user")
    back_image = fields.Image(
        '身份证国徽面', required=True, groups="hr.group_hr_user")
    handle_image = fields.Image('手持身份证', groups="hr.group_hr_user")

    @api.depends('idcard_no')
    def _compute_birthday(self):
        for record in self:
            if record.idcard_no:
                ori_birthday = self.idcard_no[6:14]
                record.birthday = datetime(
                    int(ori_birthday[0:4]), int(ori_birthday[4:6]), int(ori_birthday[6:]))

    def _is_valid_idcard(self, idcard_no):
        # 加权因子表
        factors = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        # 校验码表
        ckcodes = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')

        if isinstance(idcard_no, int):
            idcard_no = str(idcard_no)

        if not re.match(IDCARD_REGEX, idcard_no):
            return False

        items = [int(item) for item in idcard_no[:-1]]
        # 计算17位数字各位数字与对应的加权因子的乘积
        copulas = sum([a * b for a, b in zip(factors, items)])
        return ckcodes[copulas % 11].upper() == idcard_no[-1].upper()

    @api.constrains('idcard_no')
    def _check_idcard_no(self):
        for record in self:
            if not self._is_valid_idcard(record.idcard_no):
                raise ValidationError(_('身份证号码验证失败！'))
