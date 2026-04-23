# -*- coding: utf-8 -*-
{
    'name': '云腾智慧外部API管理',
    'version': '17.0.2.0',
    'description':
        """
外部API调用权限和次数管理
        """,
    'summary': '云腾智慧外部API管理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'Hidden',
    'sequence': 99,
    'depends': ['base', 'mail', 'galaxy_common'],
    'data': [
        'security/galaxy_external_api_security.xml',
        'security/ir.model.access.csv',
        'data/external_api_data.xml',
        'views/galaxy_external_api_views.xml',
        'views/galaxy_external_api_attachment_views.xml',
        'views/galaxy_external_api_action_views.xml',
        'views/galaxy_external_api_auth_views.xml',
        'views/galaxy_external_api_category_views.xml',
        'views/galaxy_external_api_resp_parser_views.xml',
        'views/galaxy_external_api_request_views.xml',
        'views/galaxy_external_api_menu_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'galaxy_external_api/static/src/scss/galaxy_external_api.scss',
        ]
    }
}