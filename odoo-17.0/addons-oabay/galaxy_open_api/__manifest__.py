# -*- coding: utf-8 -*-
{
    'name': '云腾智慧开放平台',
    'version': '2.0',
    'description':
        """
云腾智慧开放平台
        """,
    'summary': '云腾智慧开放平台',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'GalaxyBase/ExternalAPI',
    'sequence': 99,
    'depends': ['base', 'mail', 'galaxy_common'],
    'data': [
        'security/galaxy_open_api_security.xml',
        'security/ir.model.access.csv',
        'views/galaxy_open_api_menu_views.xml',
        'views/galaxy_open_api_views.xml',
        'views/galaxy_open_api_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
    }
}
