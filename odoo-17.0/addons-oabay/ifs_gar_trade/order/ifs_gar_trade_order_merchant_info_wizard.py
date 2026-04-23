# -*- coding: utf-8 -*-

from odoo import _, api, models, fields


class GuaranteeAccountsRecvTradeOrderMerchantInfoWizard(models.TransientModel):
    _name = 'ifs.gar.trade.order.merchant.info.wizard'
    _inherit = 'ifs.gar.order.step'
    _description = '目标企业确认向导'

    trade_order_id = fields.Many2one(
        'ifs.gar.trade.order', string='交易订单', required=True)
    merchant_id = fields.Many2one(
        'ifs.partner.merchant', string='采购方', related='trade_order_id.merchant_id', required=True)
    merchant_code = fields.Char('采购方编号', related="merchant_id.seq_code")
    definition_id = fields.Many2one(
        'galaxy.external.api.definition', string='结果定义', related='merchant_id.definition_id')
    json_datas = fields.Properties(
        '结果数据', definition='definition_id.params_definition', related='merchant_id.json_datas')
    key_person_ids = fields.One2many(
        'ifs.base.company.detail', string='主要人员', related='merchant_id.key_person_ids')
    merchant_approved_quota = fields.Monetary(
        "授信额度", compute='_compute_quota_info')#此处直接用关联字段存在问题，没有过滤掉当前采购方在其他方的相关额度信息，所以使用计算字段，同时其他额度信息也会变正常
    merchant_available_quota = fields.Monetary(
        "可用额度", related='merchant_id.available_quota')
    merchant_used_quota = fields.Monetary(
        "已用额度", related='merchant_id.used_quota')
    business_license = fields.Binary(
        "营业执照", related='merchant_id.business_license')

    currency_id = fields.Many2one(
        'res.currency', related='merchant_id.currency_id')
    
    @api.depends('merchant_id')
    def _compute_quota_info(self):
        for record in self:
            if record.merchant_id:
                record.merchant_approved_quota = record.merchant_id.approved_quota
            else:
                record.merchant_approved_quota = False

    def action_approved_quota(self):
        self.ensure_one()
        sub_loan_account_id = self.env['ifs.gar.sub.loan.account'].search([('supplier_id', '=', self.trade_order_id.supplier_id.id), ('merchant_id', '=', self.merchant_id.id)])
        if sub_loan_account_id:
            return {
                'name': _('子账户列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.sub.loan.account',
                'res_id': False,
                'domain': [('id', '=', sub_loan_account_id.id)],
                'target': 'new',
            }

    def action_available_quota(self):
        self.ensure_one()
        if self.merchant_id:
            return {
                'name': _('订单列表'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'ifs.gar.trade.order',
                'res_id': False,
                'domain': [('merchant_id', '=', self.merchant_id.id)],
                'target': 'new',
            }

    def action_used_quota(self):
        pass
