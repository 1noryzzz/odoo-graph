# -*- coding: utf-8 -*-
{
    'name': 'OTP动态令牌',
    'version': '17.0.1.0',
    'description':
        """
One Time Password 动态令牌服务
========================

维护动态令牌设备的信息，并验证给定的设备和验证码是否正确
        """,
    'summary': 'OTP动态令牌维护和验证',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'GalaxyBase/Base',
    'depends': [
        'base',
        'mail',
        'galaxy_common',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/one_time_passwd_views.xml',
        'wizard/otp_check_views.xml',
        'wizard/otp_sync_views.xml',
    ],
    'auto_install': False,
    'application': True,
    'assets': {
    }
}