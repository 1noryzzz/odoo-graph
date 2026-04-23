# -*- coding: utf-8 -*-

{
    'name': '账户管理(药约约)',
    'version': '2.0',
    'description':
        """
鸥贝云
=============================
鸥贝云产品涉及账户和计财的部分
        """,
    'summary': '鸥贝云产品涉及账户和计财的部分',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Account',
    'sequence': 6,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_partner',
        'ifs_gar_partner_relationship',
        'ifs_gar_invite',
        'ifs_gar_entry',
        'ifs_gar_review',
    ],
    'data': [
        'security/ifs_gar_account_security.xml',
        'security/ir.model.access.csv',
        'security/ifs_gar_account_users.xml',
        'security/ifs_gar_account_rules.xml',
        'data/ir_sequence_data.xml',
        'data/fee_type_data.xml',
        'views/ifs_base_company_views.xml',
        'views/ifs_gar_invite_supplier_views.xml',
        'views/ifs_gar_partner_fee_solution_views.xml',
        'views/ifs_gar_partner_fee_mode_views.xml',
        'views/ifs_gar_partner_interest_solution_views.xml',
        'views/ifs_gar_upgrade_quota_apply_views.xml',
        'views/ifs_gar_loan_account_bill_views.xml',
        'views/ifs_gar_sub_loan_account_views.xml',
        'views/ifs_partner_supplier_views.xml',
        'views/ifs_partner_merchant_views.xml',
        'views/ifs_gar_partner_factor_supplier_views.xml',
        'views/ifs_gar_entry_supplier_views.xml',
        'views/ifs_gar_account_menu_views.xml',
        'wizard/ifs_gar_invite_supplier_wizard_views.xml',
        'wizard/ifs_gar_invite_supplier_fee_wizard_views.xml',
        'entry/ifs_gar_entry_supplier_base_info_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ifs_gar_account/static/src/views/**/*',
        ],
    }
}