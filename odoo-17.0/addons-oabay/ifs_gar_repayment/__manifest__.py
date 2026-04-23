# -*- coding: utf-8 -*-
{
    'name': '账单还款',
    'version': '2.0',
    'description':
        """
账单及还款
=============================================
采购方订单到期生成账单，还款
        """,
    'summary': '采购方还款及后续处理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Account',
    'sequence': 9,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_gar_partner_relationship',
        'ifs_gar_account',
        'ifs_gar_trade',
    ],
    'data': [
        'security/ifs_gar_repayment_security.xml',
        'security/ifs_gar_repayment_order_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/ifs_gar_trade_order_views.xml',
        'views/ifs_gar_payment_plan_views.xml',
        'views/ifs_gar_repayment_order_views.xml',
        'views/ifs_gar_repayment_menu_views.xml',
        'order/ifs_gar_trade_order_wizard_views.xml',
        'order/ifs_gar_trade_order_payment_plan_wizard_views.xml',
        'wizard/ifs_gar_payment_plan_receipt_wizard_views.xml',
        'wizard/ifs_gar_payment_plan_withdraw_wizard_views.xml',
        'wizard/ifs_gar_trade_order_circuit_breaker_wizard_views.xml',
        'wizard/ifs_gar_trade_order_withdrawal_confirm_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ifs_gar_repayment/static/src/scss/ifs_gar_repayment.scss',
        ]
    }
}
