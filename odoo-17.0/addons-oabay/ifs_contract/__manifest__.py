# -*- coding: utf-8 -*-
{
    'name': '合同管理',
    'version': '2.0',
    'description':
        """
普惠金融相关的合同模板及合同签署管理
========================

维护基本的合同模板，并管理合同相关的基本信息
        """,
    'summary': '合同模板和签署管理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Contract',
    'sequence': 14,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'galaxy_open_api',
        'ifs_base',
    ],
    'data': [
        'security/ifs_contract_security.xml',
        'security/ir.model.access.csv',
        'data/ifs_contract_users.xml',
        'data/ifs_contract_cron.xml',
        'data/ifs_contract_data.xml',
        'views/ifs_contract_menu_views.xml',
        'views/ifs_contract_category_views.xml',
        'wizard/ifs_contract_template_preview.xml',
        'views/ifs_contract_template_views.xml',
        'views/ifs_contract_info_views.xml',
        'views/ifs_contract_sign_template.xml',
        'views/res_config_settings_views.xml',
        'views/galaxy_open_api_views.xml',
        'report/ifs_contract_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
        'web.assets_backend': [
            # 'ifs_contract/static/src/js/contract_sign.js',
        ],
        'web.assets_frontend': [
            'ifs_contract/static/src/scss/*.scss',
            'ifs_contract/static/src/js/contract_share_tips.js',
        ],
    }
}