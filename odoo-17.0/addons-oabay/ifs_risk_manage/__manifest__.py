# -*- coding: utf-8 -*-
{
    'name': '风险管控',
    'version': '2.0',
    'description':
        """
风险管控
=====================================================
综合系统数据及第三方数据源，识别和管理金融业务场景下的风险
        """,
    'summary': '识别和管理金融业务场景下的风险',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Base',
    'sequence': 16,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_base',
    ],
    'data': [
        'security/ifs_risk_manage_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_risk_manage.xml',
        'data/ir_sequence_data.xml',
        'data/galaxy_bairong_data.xml',
        'views/ifs_risk_manage_menu_views.xml',
        'views/ifs_risk_manage_credits_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/ifs_risk_manage_credits_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
    }
}
