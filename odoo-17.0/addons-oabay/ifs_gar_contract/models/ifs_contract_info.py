# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class InclusiveFinancingContractInformation(models.Model):
    _inherit = 'ifs.contract.info'

    partner_one = fields.Reference(selection_add=[
        ('ifs.gar.invite.supplier', '受邀供应方'),
        ('ifs.gar.invite.franchisee', '受邀合伙人'),
        ('ifs.gar.invite.lawfirm', '受邀律师事务所'),
        ('ifs.gar.invite.merchant', '受邀采购方'),
        ('ifs.gar.entry.supplier', '供应方进件'),
        ('ifs.gar.entry.merchant', '采购方进件'),
        ('ifs.gar.entry.franchisee', '合伙人进件'),
        ('ifs.gar.entry.lawfirm', '律师事务所进件'),
    ])
    partner_two = fields.Reference(selection_add=[
        ('ifs.gar.invite.supplier', '受邀供应方'),
        ('ifs.gar.invite.franchisee', '受邀合伙人'),
        ('ifs.gar.invite.lawfirm', '受邀律师事务所'),
        ('ifs.gar.invite.merchant', '受邀采购方'),
        ('ifs.gar.entry.supplier', '供应方进件'),
        ('ifs.gar.entry.merchant', '采购方进件'),
        ('ifs.gar.entry.franchisee', '合伙人进件'),
        ('ifs.gar.entry.lawfirm', '律师事务所进件'),
    ])
    partner_three = fields.Reference(selection_add=[
        ('ifs.gar.invite.supplier', '受邀供应方'),
        ('ifs.gar.invite.franchisee', '受邀合伙人'),
        ('ifs.gar.invite.lawfirm', '受邀律师事务所'),
        ('ifs.gar.invite.merchant', '受邀采购方'),
        ('ifs.gar.entry.supplier', '供应方进件'),
        ('ifs.gar.entry.merchant', '采购方进件'),
        ('ifs.gar.entry.franchisee', '合伙人进件'),
        ('ifs.gar.entry.lawfirm', '律师事务所进件'),
    ])
    partner_four = fields.Reference(selection_add=[
        ('ifs.gar.invite.supplier', '受邀供应方'),
        ('ifs.gar.invite.franchisee', '受邀律师事务所'),
        ('ifs.gar.invite.lawfirm', '受邀合伙人'),
        ('ifs.gar.invite.merchant', '受邀采购方'),
        ('ifs.gar.entry.supplier', '供应方进件'),
        ('ifs.gar.entry.merchant', '采购方进件'),
        ('ifs.gar.entry.franchisee', '律师事务所进件'),
        ('ifs.gar.entry.lawfirm', '合伙人进件'),
    ])

    def contract_edit(self):
        self.ensure_one()

        return {
            'name': f'编辑合同 - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ifs.contract.info',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [[self.env.ref('ifs_gar_contract.ifs_contract_info_view_form_edit').id, 'form']],
            'target': 'new',
            'res_id': self.id,
        }
