# -*- coding: utf-8 -*-
{
    'name': '订单用信',
    'version': '2.0',
    'description':
        """
订单发起和用信
=============================================
供应方发起订单，采购方确认并完成贷款转贷款
        """,
    'summary': '供应方发起订单，让采购方完成信用付',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Account',
    'sequence': 7,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_base',
        'ifs_gar_partner_relationship',
        'ifs_gar_entry',
        'ifs_gar_review',
        'ifs_gar_account',
    ],
    'data': [
        'security/ifs_gar_trade_security.xml',
        'security/ifs_gar_trade_order_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/sms_template_setting.xml',
        'data/ifs_gar_trade_config_data.xml',
        'data/ifs_gar_trade_definition_data.xml',
        'data/ifs_gar_trade_order_config_detail_data.xml',
        'data/ifs_gar_trade_reduce_reasons_data.xml',
        'views/ifs_partner_merchant_views.xml',
        'views/ifs_gar_trade_order_views.xml',
        # 'views/ifs_gar_loan_account_bill_views.xml',
        'views/ifs_gar_trade_order_config_views.xml',
        'views/ifs_gar_payment_order_views.xml',
        'views/ifs_gar_trade_menu_views.xml',
        'views/ifs_gar_trade_modify_password_template.xml',
        'views/ifs_gar_trade_mobile_cashier_template.xml',
        'views/ifs_gar_trade_mobile_pay_result_template.xml',
        'views/ifs_gar_trade_mobile_change_pwd_template.xml',
        'views/ifs_gar_trade_mobile_bill_template.xml',
        'order/ifs_gar_order_step_views.xml',
        'order/ifs_gar_trade_order_wizard_views.xml',
        'order/ifs_gar_trade_order_merchant_info_wizard_views.xml',
        'order/ifs_gar_trade_order_withdrawal_info_wizard_views.xml',
        'wizard/ifs_gar_trade_order_merchant_selector_wizard_views.xml',
        'wizard/ifs_gar_trade_order_withdrawal_confirm_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ifs_gar_trade/static/src/views/**/*',
            'ifs_gar_trade/static/scss/trade_order.scss',
        ],
        'web.assets_frontend': [
            'ifs_gar_trade/static/src/js/modify_password.js',
            'ifs_gar_trade/static/src/js/*.js',
            'ifs_gar_trade/static/src/scss/*.scss',
        ],
    }
}