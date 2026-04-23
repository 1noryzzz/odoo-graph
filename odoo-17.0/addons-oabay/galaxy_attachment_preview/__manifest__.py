# -*- coding: utf-8 -*-
{
    'name': '二进制字段预览',
    'version': '17.0.1.0',
    'description':
        """
二进制字段预览
========================
提供图片、PDF等字段的统一预览
        """,
    'summary': '二进制字段预览',
    'author': 'Ferren Liu',
    'company': 'Galaxy',
    'maintainer': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'GalaxyBase/Component',
    'depends': ['base', 'mail'],
    'data': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        # 'galaxy_attachment_preview.assets_messaging': [
        #     'galaxy_attachment_preview/static/src/models/*.js'
        # ],
        'web.assets_backend': [
            # ('include', 'galaxy_attachment_preview.assets_messaging'),
            'galaxy_attachment_preview/static/src/views/**/*',
            'galaxy_attachment_preview/static/src/core/**/*',
        ],
    },
}
