# -*- coding: utf-8 -*-

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WorkUser(models.Model):

    _inherit = ['wechat.work.user']

    enable = fields.Integer('Enable')  # TODO: onchange
    employee_ids = fields.One2many(
        'hr.employee', 'work_user_id', string='Employees')
    main_department = fields.Integer("Work Department Id")
    isleader = fields.Integer('Is Leader')
    department = fields.Char("Department List")
    order = fields.Char("Order List")
    is_leader_in_dept = fields.Char("Is Leader List")

    def _parse_values(self, values):
        if 'department' in values:
            values['department'] = json.dumps(values['department'])
        if 'order' in values:
            values['order'] = json.dumps(values['order'])
        if 'isleader' in values and values['isleader'] == 1 and 'is_leader_in_dept' in values:
            values['is_leader_in_dept'] = json.dumps(
                values['is_leader_in_dept'])

        return super(WorkUser, self)._parse_values(values)

    def update_department_manager(self, company_id):
        for work_user in self:
            if work_user.isleader == 1 and \
                    work_user.department and \
                    work_user.is_leader_in_dept:
                new_manager_id = work_user.employee_ids.filtered(
                    lambda x: x.company_id.id == company_id).id
                dpt_infos = list(
                    zip(json.loads(work_user.department),
                        json.loads(work_user.is_leader_in_dept)))
                for (work_dpt_id, is_leader) in dpt_infos:
                    if is_leader != 1:
                        continue

                    dpt = self.env['hr.department'].search([
                        '&', ('company_id', '=', company_id),
                        ('work_department_id', '=', work_dpt_id)])
                    if dpt.exists() and new_manager_id != dpt.manager_id.id:
                        dpt.write({
                            'manager_id': new_manager_id
                        })

    def _change_department(self, msg):
        if not super(WorkUser, self)._change_department(msg):
            return self.env['hr.department'].update_department(msg)

        return False

    def _change_contact_detail(self, msg, user_info):
        self.ensure_one()

        if not super(WorkUser, self)._change_contact_detail(msg, user_info):
            self.env['hr.employee'].update_employee(self, user_info)
            if self.status == 1:
                self.update_department_manager(self.env.company.id)

            return True

        return False
