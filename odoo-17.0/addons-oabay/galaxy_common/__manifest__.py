# -*- coding: utf-8 -*-
{
    'name': '云腾智慧公共库',
    'version': '17.0.1.1',
    'description':
        """
云腾智慧公共库
========================

此模块提供全局的公共功能，比如添加地区表，添加对多数据库的支持等
        """,
    'summary': '云腾智慧公共库',
    'author': 'Ferren Liu',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'Hidden',
    'depends': ['base', 'web', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/http_routing_template.xml',
        'views/base_external_dbsource.xml',
        'views/webclient_templates.xml',
        'views/website_templates.xml',
        'views/res_config_settings_views.xml',
        'views/sms_sms_views.xml',
        'views/sms_template_views.xml',
        'wizard/sms_template_preview_views.xml',
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_frontend': [
            'galaxy_common/static/src/core/**/*',
        ],
        'web.assets_backend': [
            'galaxy_common/static/lib/highlight/highlight.min.js',
            'galaxy_common/static/lib/highlight/styles/default.min.css',
            'galaxy_common/static/src/core/**/*',
            'galaxy_common/static/src/views/**/*',
            'galaxy_common/static/src/js/user_menu.js',
            'galaxy_common/static/src/webclient/webclient.js',
        ],
    },
}
