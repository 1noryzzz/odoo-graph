# -*- coding: utf-8 -*-

{
    'name': '君子签',
    'version': '2.0',
    'description':
        """
合同管理中，调用外部签署接口君子签
========================

外部接口实现
        """,
    'summary': '调用君子签合同签署接口',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Contract',
    'sequence': 24,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ifs_sign_jzq_data.xml',
        'views/res_config_settings_views.xml',
        'data/jzq_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}