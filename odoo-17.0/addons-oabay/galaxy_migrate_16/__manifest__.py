# -*- coding: utf-8 -*-
{
    'name': '云腾智慧迁移工具',
    'version': '1.0',
    'description':
        """
云腾智慧迁移工具
========================

把数据从odoo 15 迁移到 odoo 16
        """,
    'summary': '云腾智慧公共库',
    'author': 'Ferren Liu',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'Hidden',
    'depends': ['base', 'web', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/galaxy_migrate_data.xml',
        'views/galaxy_migrate_data_api.xml',
        'views/picker.xml'
    ],
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_frontend': [
            'galaxy_migrate_16/static/src/css/picker.css',
            # 'galaxy_migrate_16/static/src/js/picker.js',
        ],
    },
}
