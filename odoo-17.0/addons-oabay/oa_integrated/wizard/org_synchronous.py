# -*- coding: utf-8 -*-
import threading
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OrganizationSynchronous(models.TransientModel):
    _name = 'oa.org.synchronous'
    _description = "组织结构同步"

    RepeatType = [('mobile', '以手机号')]

    company_ids = fields.Many2many(
        'res.company', 'oa_org_sync_companys_rel', string="要同步的公司", required=True,
        default=lambda self: [(6, 0, [self.env.company.id])])
    department = fields.Boolean(string=u'同步部门', default=True)
    synchronous_dept_detail = fields.Boolean(string=u'同步部门详情', default=True)
    repeat_type = fields.Selection(
        string=u'判断唯一', selection=RepeatType, default='mobile')
    employee = fields.Boolean(string=u'同步员工', default=True)
    
    @api.threading
    def _do_synchronous(self):
        try:
            if self.department:
                self.synchronous_department(self.repeat_type)
            if self.employee:
                self.synchronous_employee(self.repeat_type)
            if self.synchronous_dept_detail:
                self.get_department_details()
        except Exception as e:
            raise UserError(e)

    def start_synchronous_data(self):
        """
        基础数据同步
        :return:
        """
        self.ensure_one()
        threading.Thread(target=self._do_synchronous, args=([])).start()
        return {'type': 'ir.actions.act_window_close'}

    def synchronous_department(self, repeat_type=None):
        """
        同步部门
        :return:
        """
        _logger.warning("---synchronous_department not implement---")
        pass

    def get_department_details(self):
        """
        获取部门详情
        :return:
        """
        _logger.warning("---get_department_details not implement---")
        pass

    def synchronous_employee(self, repeat_type=None):
        """
        同步部门员工列表
        :return:
        """
        _logger.warning("---synchronous_employee not implement---")
        pass
