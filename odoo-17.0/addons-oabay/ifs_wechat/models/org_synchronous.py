# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OrganizationSynchronous(models.TransientModel):
    _inherit = 'oa.org.synchronous'
    _description = "组织结构同步"

    def org_synchronous(self):
        try:
            result = False
            if not self._context.get('start_index', False) and self.department:
                result = self.env['hr.department'].wechat_sync()
            if self._context.get('start_index', False) and self.employee:
                end_index, all_num = self.synchronous_employee(
                    self._context.get('start_index'))
                if end_index and all_num and end_index < all_num:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'org_synchronous_button',
                        'params': {
                            'type': 'success',
                            'message': _('部门导入成功！员工信息成功导入 %d /总共 %d' % (end_index, all_num)) 
                                if result else _('员工信息成功导入 %d /总共 %d' % (end_index, all_num)),
                            'start_index': end_index,
                        }
                    }
        except Exception as e:
            raise UserError(e)
