# -*- coding: utf-8 -*-
{
    'name': '微信集成',
    'version': '2.0',
    'description':
        """
普惠金融项目下，与微信集成
========================

项目描述
        """,
    'summary': '普惠金融场景下，集成微信相关的功能和能力',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Wechat',
    'sequence': 15,
    'depends': [
        'base',
        'mail',
        'wechat',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        # 'data/wechat_offiaccount.xml',
        'views/ifs_wechat_menu_views.xml',
        'views/org_synchronous_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_backend': [
            'ifs_wechat/static/src/js/*.js',
        ],
    }
}