# -*- coding: utf-8 -*-
{
    'name': '阿里云接口',
    'version': '17.0.2.0',
    'description':
        """
阿里云接口管理模块
========================

管理和对接阿里云接口
        """,
    'summary': '云腾智慧公用的阿里云接口管理模块',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'GalaxyBase/ExternalAPI',
    'sequence': 10,
    'depends': [
        'base',
        'mail',
        'sms',
        'galaxy_common',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/galaxy_aliyun_data.xml',
        'views/res_config_settings_views.xml',
        'views/sms_template_views.xml',
        'views/sms_sms_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'galaxy_aliyun/static/src/ali-oss/aliyun-oss-sdk.min.js',
            'galaxy_aliyun/static/src/core/**/*',
            'galaxy_aliyun/static/src/oss_upload_progress.*',
            'galaxy_aliyun/static/src/oss_uploading_block_ui.*',
            'galaxy_aliyun/static/src/views/**/*',
        ]
    }
}
