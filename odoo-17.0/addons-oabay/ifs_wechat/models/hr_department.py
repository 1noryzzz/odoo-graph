# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Department(models.Model):
    _inherit = "hr.department"
    _order = "parent_id"

    work_department_id = fields.Integer('Department Id in Wechat Work')
    work_parent_department_id = fields.Integer(
        'Parent Department Id in Wechat Work')

    def _parse_values(self, values):
        if 'id' in values:
            values['work_department_id'] = values['id']
            values.pop('id')
        if 'name' in values:
            values['complete_name'] = values['name']
        if 'parentid' in values:
            values['work_parent_department_id'] = values['parentid']
        if 'order' in values:
            values['sequence'] = values['order']

        values['active'] = True
        values['company_id'] = self.env.company.id

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def _update_parent_relationship(self):
        hr_departments = self.search(
            [('company_id', '=', self.env.company.id), ('work_department_id', '!=', False)])
        for hr_department in hr_departments:
            if hr_department.work_parent_department_id > 0:
                parent_dpt = hr_departments.filtered(
                    lambda x: x.work_department_id == hr_department.work_parent_department_id)
                if parent_dpt.exists():
                    hr_department.write({
                        'parent_id': parent_dpt.id
                    })

    def update_department(self, msg):
        corp_id = msg.target
        wechat_work, entry = self.env['wechat.work.config'].retrieve_entry(
            corp_id=corp_id)

        department = self.with_context(active_test=False).search(
            ['&', ('company_id', '=', self.env.company.id),
             ('work_department_id', '=', msg.department_id)])
        if msg.change_type == 'delete_party':
            if department.exists():
                department.write({
                    'active': False
                })

                self.env.flush_all()
                self._update_parent_relationship()
            return True
        elif msg.change_type in ['create_party', 'update_party']:
            dpt_infos = entry.contacts_client.department.get(msg.department_id)
            for dpt_info in dpt_infos:
                dpt_record = self._parse_values(dpt_info)
                if dpt_record.get('work_department_id') == msg.department_id:
                    if department.exists():
                        department.write(dpt_record)
                    else:
                        self.create(dpt_record)

                    self.env.flush_all()
                    self._update_parent_relationship()
                    break

            return True

        return False

    @api.model
    def wechat_sync(self):
        wechat_work, entry = self.env['wechat.work.config'].retrieve_entry()
        if not entry.app_id:
            raise ValidationError('Wechat Work Uninitialized')

        hr_departments = self.with_context(active_test=False).search(
            [('company_id', '=', self.env.company.id), ('work_department_id', '!=', False)])
        hr_departments.write({
            'active': False
        })

        dpt_infos = entry.contacts_client.department.get(1)
        for dpt_info in dpt_infos:
            dpt_record = self._parse_values(dpt_info)
            exist_dpt = hr_departments.filtered(
                lambda x: x.work_department_id == dpt_record.get('work_department_id'))
            if exist_dpt.exists():
                exist_dpt.write(dpt_record)
            else:
                self.create(dpt_record)

        self.env.flush_all()
        self._update_parent_relationship()

        return True
