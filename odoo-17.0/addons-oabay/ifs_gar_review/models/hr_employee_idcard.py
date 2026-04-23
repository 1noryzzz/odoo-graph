# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class EmployeeIDcard(models.Model):
    _inherit = 'hr.employee.idcard'

    def create_legal_from_entry(self, entry_model):
        """
        从进件信息创建法人身份证信息
        """
        idcard = self.env['hr.employee.idcard'].sudo().search([
            ('idcard_no', '=', entry_model.legal_id_number)
        ])
        if idcard.exists() and idcard.employee_ids.filtered(
                lambda e: e.id != entry_model.root_employee_id.id and e.company_id.id == entry_model.company_id.id).exists():
            raise ValidationError(_('身份证号码已存在，并已被其他用户绑定！'))

        user_info = {
            'name': entry_model.legal_name,
            'idcard_no': entry_model.legal_id_number,
            'nationality': entry_model.legal_nationality,
            'gender': entry_model.legal_gender,
            'birthday': entry_model.legal_birthday,
            'address': entry_model.legal_address,
            'authority': entry_model.legal_authority,
            'start_date': entry_model.legal_start_date,
            'end_date': entry_model.legal_end_date,
            'front_image': entry_model.legal_front_image,
            'back_image': entry_model.legal_back_image,
        }
        if idcard.exists():
            idcard.write(user_info)
        else:
            idcard = self.env['hr.employee.idcard'].create(user_info)

        return idcard

    def create_guarantor_from_entry(self, entry_model):
        """
        从进件信息创建担保人身份证信息
        """
        idcard = self.env['hr.employee.idcard'].sudo().search([
            ('idcard_no', '=', entry_model.guarantor_idcard_no)
        ])
        if idcard.exists() and idcard.employee_ids.filtered(
                lambda e: e.id != entry_model.guarantor_employee_id.id and e.company_id.id == entry_model.company_id.id).exists():
            raise ValidationError(_('身份证号码已存在，并已被其他用户绑定！'))

        user_info = {
            'name': entry_model.guarantor_name,
            'idcard_no': entry_model.guarantor_idcard_no,
            'nationality': entry_model.guarantor_nationality,
            'gender': entry_model.guarantor_gender,
            'birthday': entry_model.guarantor_birthday,
            'address': entry_model.guarantor_address,
            'authority': entry_model.guarantor_authority,
            'start_date': entry_model.guarantor_start_date,
            'end_date': entry_model.guarantor_end_date,
            'front_image': entry_model.guarantor_front_image,
            'back_image': entry_model.guarantor_back_image,
        }
        if idcard.exists():
            idcard.write(user_info)
        else:
            idcard = self.env['hr.employee.idcard'].create(user_info)

        return idcard
