# -*- coding: utf-8 -*-


import logging


from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class InclusiveFinancingContractInforSignToken(models.TransientModel):
    _inherit = 'ifs.contract.info.sign.token'

    sign_partner = fields.Reference(
        selection_add=[
            ('ifs.gar.trade.order', '交易订单'),
            ('ifs.partner.supplier', '供应方'),
            ('ifs.partner.merchant', '采购方'),
            ('ifs.partner.franchisee', '合伙人'),
            ('ifs.partner.lawfirm', '律师事务所'),
            ('ifs.gar.entry.supplier','供应商进件'),
            ('ifs.gar.entry.merchant','采购方进件'),
            ('ifs.gar.entry.franchisee','合伙人进件'),
            ('ifs.gar.entry.lawfirm','律师事务所进件'),
            ('ifs.gar.upgrade.quota.apply', '额度调整申请'),
        ])
    
    ref_object = fields.Reference(
        selection_add=[
            ('ifs.gar.trade.order', '交易订单'),
            ('ifs.partner.supplier', '供应商'),
            ('ifs.partner.franchisee', '合伙人'),
            ('ifs.partner.lawfirm', '律师事务所'),
            ('ifs.gar.entry.supplier.contract.wizard','供应商进件'),
            ('ifs.gar.entry.supplier','供应商进件'),
            ('ifs.gar.entry.merchant.contract.wizard','采购方进件'),
            ('ifs.gar.entry.merchant.approval.info.wizard', '采购方进件-签约'),
            ('ifs.gar.upgrade.quota.apply', '额度调整申请'),
            ('ifs.gar.entry.franchisee.contract.wizard', '合伙人进件流程--合同协议'),
            ('ifs.gar.entry.lawfirm.contract.wizard', '律师事务所进件流程--合同协议'),
            ('ifs.gar.entry.merchant', '采购方进件'),
            ('ifs.gar.trade.order.circuit.breaker.wizard', '订单熔断'),
        ])
