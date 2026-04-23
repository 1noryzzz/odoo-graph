# -*- coding: utf-8 -*-
{
    'name': '合作伙伴自动补全',
    'version': '2.0',
    'description':
        """
合作伙伴自动补全组件
===============================================
通过用户在输入框中输入的信息，自动补全合作伙伴信息
        """,
    'summary': '合作伙伴自动补全',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Partner',
    'sequence': 99,
    'depends': ['base', 'mail', 'partner_autocomplete', 'ifs_base'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'ifs_partner_autocomplete/static/src/js/partner_autocomplete_fieldchar.js',
        ],
    }
}
