# -*- coding: utf-8 -*-


import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):

    _inherit = ['hr.employee']

    work_user_id = fields.Many2one(
        'wechat.work.user', required=False, ondelete='restrict', auto_join=True,
        string='Wechat Work User')

    def _parse_work_values(self, values, hr_departments):
        if 'gender' in values:
            if values['gender'] in ["1", "male"]:
                values['gender'] = 'male'
            elif values['gender'] in ["2", "female"]:
                values['gender'] = 'female'
            else:
                values['gender'] = 'other'
        # TODO: job_id
        if 'position' in values:
            values['job_title'] = values['position']
        if 'external_position' in values:
            values['external_job_title'] = values['external_position']
        if 'address' in values:
            values['work_location'] = values['address']
        if 'main_department' in values:
            departments = hr_departments.filtered(
                lambda x: x.work_department_id == values['main_department'])
            if departments.exists():
                values['department_id'] = departments[0].id

        _vals = {}
        if 'status' in values and values['status'] == 5:
            _vals['active'] = False
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def update_employee(self, work_user, employee_info):
        hr_departments = self.env['hr.department'].search(
            [('company_id', '=', self.env.company.id)])
        employee_record = self._parse_work_values(employee_info, hr_departments)
        employee_record.update({
            'company_id': self.env.company.id,
        })

        employee = self.env['hr.employee'].with_context(active_test=False).search(
            ['&', ('company_id', '=', employee_record.get('company_id')),
                ('work_user_id.work_userid', '=',
                 employee_info.get('userid'))])
        if employee.exists():
            employee_record['user_id'] = employee.user_id.id
            employee.write(employee_record)
        elif 'active' not in employee_record or employee_record.get('active'):
            employee_record.update({
                'user_id': work_user.user_id.id,
                'work_user_id': work_user.id
            })
            self.create(employee_record)

    @api.model
    def wechat_sync(self, start_index):
        sync_max_line = 10
        wechat_work, entry = self.env['wechat.work.config'].retrieve_entry()
        if not entry.app_id:
            raise ValidationError('Wechat Work Uninitialized')

        hr_departments = self.env['hr.department'].search(
            [('company_id', '=', self.env.company.id)])

        work_user_ids = []
        all_work_userids = []
        current_line_index = 0
        employee_infos = entry.contacts_client.user.list(1, True)
        for employee_info in employee_infos:
            all_work_userids.append(employee_info.get('userid'))

            if current_line_index < start_index:
                current_line_index += 1
                continue

            if current_line_index - start_index >= sync_max_line:
                break

            employee_record = self._parse_work_values(employee_info, hr_departments)
            employee_record.update({
                'company_id': self.env.company.id,
            })

            employee = self.env['hr.employee'].with_context(active_test=False).search(
                ['&', ('company_id', '=', employee_record.get('company_id')),
                 ('work_user_id.work_userid', '=',
                  employee_info.get('userid'))])
            if employee.exists():
                employee_record['user_id'] = employee.user_id.id
                employee.write(employee_record)
                work_user = employee.work_user_id.update_from_wechat_work(
                    wechat_work, employee_info)
                work_user_ids.append(work_user.id)
            else:
                work_user = self.env['wechat.work.user'].update_from_wechat_work(
                    wechat_work, employee_info)
                work_user_ids.append(work_user.id)
                employee_record.update({
                    'user_id': work_user.user_id.id,
                    'work_user_id': work_user.id
                })
                self.create(employee_record)

            self.env.cr.commit()
            _logger.info('sync line index is %d' % current_line_index)
            current_line_index += 1

        self.env['wechat.work.user'].browse(
            work_user_ids).update_department_manager(self.env.company.id)

        _logger.info('sync wechat work user total: %s' %
                     (current_line_index - start_index))

        has_next = (len(employee_infos) > current_line_index)

        if not has_next:
            removed_employees = self.env['hr.employee'].search(
                ['&', ('work_user_id.work_id', '=', wechat_work.id),
                 ('work_user_id.work_userid', 'not in', all_work_userids)])
            if removed_employees.exists():
                for emp in removed_employees:
                    work_user = emp.work_user_id.update_from_wechat_work(
                        wechat_work, {
                            'userid': emp.work_user_id.work_userid,
                            'status': 5,
                            'enable': 0
                        })

                    emp.write({
                        'active': False
                    })

        return current_line_index, len(employee_infos)
