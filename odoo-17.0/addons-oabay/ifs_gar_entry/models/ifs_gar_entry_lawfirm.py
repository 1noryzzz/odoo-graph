# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class GuaranteeAccountsRecEntryLawfirm(models.Model):
    _name = 'ifs.gar.entry.lawfirm'
    _inherit = ['ifs.gar.entry.mixin']
    _inherits = {'ifs.gar.invite.lawfirm': 'invite_id'}
    _description = '律师事务所进件流程'

    def _step_models(self):
        return [
            'ifs.gar.entry.lawfirm.cover.wizard',
            'ifs.gar.entry.lawfirm.base.info.wizard',
            'ifs.gar.entry.lawfirm.contact.wizard',
            'ifs.gar.entry.lawfirm.account.wizard',
            'ifs.gar.entry.lawfirm.resource.wizard',
            'ifs.gar.entry.lawfirm.finish.wizard',
        ]

    invite_id = fields.Many2one(
        'ifs.gar.invite.lawfirm', required=True, ondelete='restrict', index=True,
        string='邀请信息', help='此次进件对应的邀请信息', copy=True)
    last_entry_id = fields.Many2one(
        'ifs.gar.entry.lawfirm', string='上一次进件', copy=False)
    state = fields.Selection([
        ('draft', '草稿'),
        ('committed', '已提交'),
        ('rejected', '已驳回'),
        ('approval', '审批通过'),
    ], string='进件状态', default='draft', copy=False)

    business_license = fields.Binary('营业执照', copy=False)
    phone = fields.Char('电话', related='invite_id.phone', store=True, copy=True)
    email = fields.Char('邮箱', related='invite_id.email', store=True, copy=True)
    business_address = fields.Char(
        '营业地址', related='invite_id.business_address', store=True, copy=True)

    legal_front_image = fields.Image('身份证人像面', copy=False)
    legal_back_image = fields.Image('身份证国徽面', copy=False)
    legal_name = fields.Char('法人姓名', copy=False)
    legal_id_number = fields.Char('法人身份证号', copy=False)
    legal_nationality = fields.Char('民族', copy=False)
    legal_gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ], string='性别', copy=False)
    legal_birthday = fields.Char('出生日期', copy=False)
    legal_address = fields.Char('证件地址', copy=False)
    legal_authority = fields.Char('签发机关', copy=False)
    legal_start_date = fields.Char('起始日期', copy=False)
    legal_end_date = fields.Char('失效日期', copy=False)

    bank_id = fields.Many2one('res.bank', string='开户行', copy=False)
    acc_number = fields.Char('账号', copy=False)
    deposit_license = fields.Binary(string='开户证可证', copy=False)

    account_name = fields.Char(
        '账户名称', compute='_compute_account_info')
    account_no = fields.Char(
        '银行卡号', compute='_compute_account_info')
    deposit_bank = fields.Char(
        '开户行', compute='_compute_account_info')

    reception_picture = fields.Binary('前台照', copy=False)
    office_area_picture = fields.Binary('公司办公区照片', copy=False)

    @api.depends('bank_id', 'acc_number')
    def _compute_account_info(self):
        for record in self:
            acc_info = {
                'account_name': self.name,
                'account_no': '',
                'deposit_bank': '',
            }
            if self.bank_id.id:
                acc_info.update({
                    'account_no': self.acc_number,
                    'deposit_bank': self.bank_id.name,
                })
            record.update(acc_info)

    def view_entrys(self):
        return {
            'name': _('进件列表'),
            'view_mode': 'tree,form',
            'res_model': 'ifs.gar.entry.lawfirm',
            'type': 'ir.actions.act_window',
            'domain': [('ifs_company_id', '=', self.ifs_company_id.id)],
            'context': {'default_ifs_company_id': self.ifs_company_id.id},
            'target': 'current',
        }

    def start_step(self):
        if self.state == 'rejected':
            return self.create({
                'ifs_company_id': self.ifs_company_id.id,
                'invite_id': self.invite_id.id,
                'last_entry_id': self.id,
                'phone': self.invite_id.phone,
                'email': self.invite_id.email,
                'business_address': self.invite_id.business_address,
            }).start_step()
        return super().start_step()

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            if vals['state'] == 'committed':
                self.invite_id.write({
                    'state': 'activation',
                })
            elif vals['state'] == 'rejected':
                self.invite_id.write({
                    'state': 'waiting',
                })
            elif vals['state'] == 'approval':
                self.invite_id.write({
                    'state': 'ready',
                })

        return res
