# -*- coding: utf-8 -*-
{
    'name': '集成办公',
    'version': '17.0.1.0',
    'description':
        """
第三方办公软件集成
========================

与第三方办公软件，比如钉钉、企业微信、微信公众号等集成
        """,
    'summary': '集成企业微信、钉钉等第三方办公平台',
    'author': 'Ferren Liu',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'OA_Integrated/Main',
    'sequence': 1,
    'depends': ['base', 'contacts', 'hr', 'galaxy_common'],
    'data': [
        'security/oa_security.xml',
        'security/ir.model.access.csv',
        'wizard/org_synchronous.xml',
        'views/callback_action_views.xml',
        'views/oa_menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'oa_integrated/static/src/scss/style.scss',
        ]
    },
}
