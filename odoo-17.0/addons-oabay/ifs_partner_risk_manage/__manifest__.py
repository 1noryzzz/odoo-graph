# -*- coding: utf-8 -*-
{
    'name': '合作伙伴的风险管控',
    'version': '2.0',
    'description':
        """
合作伙伴的风险管控
========================

项目描述
        """,
    'summary': '为各合作伙伴增加风险管控功能',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Base',
    'sequence': 26,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_partner',
        'ifs_risk_manage',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
    }
}