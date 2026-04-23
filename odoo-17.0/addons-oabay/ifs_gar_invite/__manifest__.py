# -*- coding: utf-8 -*-
{
    'name': '鸥贝云进件邀约',
    'version': '2.0',
    'description':
        """
鸥贝云进件邀约
========================

项目描述
        """,
    'summary': '发起进件邀约，并管理进件过程',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Partner',
    'sequence': 4,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_partner',
        'ifs_base',
        'ifs_hr',
        'ifs_partner_hr',
        'ifs_gar_partner_relationship',
        # 'ifs_gar_sales',
    ],
    'data': [
        'security/ifs_gar_invite_security.xml',
        'security/ir.model.access.csv',
        'security/ifs_gar_invite_rules.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/invite_supplier_sms_data.xml',
        'views/ifs_gar_invite_menu_views.xml',
        'views/ifs_gar_invite_supplier_views.xml',
        'views/ifs_gar_invite_merchant_views.xml',
        'views/ifs_gar_invite_franchisee_views.xml',
        'views/ifs_gar_invite_lawfirm_views.xml',
        'views/mobile_portal_template.xml',
        'views/mobile_invite_supplier_template.xml',
        'views/mobile_invite_merchant_template.xml',
        'views/mobile_invite_franchisee_new_template.xml',
        'views/res_config_setting_views.xml',
        'wizard/ifs_gar_factor_selector_wizard_views.xml',
        'wizard/ifs_gar_invite_supplier_root_user_wizard_views.xml',
        'wizard/ifs_gar_invite_supplier_wizard_views.xml',
        'wizard/ifs_gar_invite_franchisee_root_user_wizard_views.xml',
        'wizard/ifs_gar_invite_franchisee_wizard_views.xml',
        'wizard/ifs_gar_invite_lawfirm_root_user_wizard_views.xml',
        'wizard/ifs_gar_invite_lawfirm_wizard_views.xml',
        'wizard/ifs_gar_invite_merchant_root_user_wizard_views.xml',
        'wizard/ifs_gar_invite_merchant_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_frontend': [
            'ifs_gar_invite/static/src/scss/portal_invite.scss',
            'ifs_gar_invite/static/src/js/franchisee_invite.js',
        ],
        'web.assets_backend': [
            'ifs_gar_invite/static/src/views/**/*',
        ],
    }
}