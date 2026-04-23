# -*- coding: utf-8 -*-

{
    'name': '普惠金融基础库',
    'version': '2.0',
    'description':
        """
普惠金融基础库
========================

主要为res_company 增加金融业务需要的信息
        """,
    'summary': '金融业务基础模块',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Base',
    'sequence': 11,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'galaxy_external_api',
        'galaxy_attachment_preview',
    ],
    'data': [
        'security/ifs_security.xml',
        'security/ir.model.access.csv',
        'security/res_company_rules.xml',
        'data/ir_sequence_data.xml',
        'data/ifs_base_data.xml',
        'views/ifs_base_company_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/ifs_steps_wizard_views.xml',
        'wizard/ifs_base_company_wizard_views.xml',
        'wizard/ifs_base_company_bank_wizard_views.xml',
        'wizard/ifs_base_company_contact_wizard_views.xml',
        'wizard/ifs_base_company_business_license_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'ifs_base/static/src/scss/ifs_base.scss',
        ]
    }
}
