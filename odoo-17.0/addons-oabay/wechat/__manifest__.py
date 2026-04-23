# -*- coding: utf-8 -*-
{
    'name': '微信集成',
    'version': '17.0.1.0',
    'description':
        """
微信集成
========================

整合微信、微信小程序和企业微信的各项功能
        """,
    'summary': '实现了微信生态相关的各项接口',
    'author': 'Ferren Liu',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'OA_Integrated/Wechat',
    'sequence': 9,
    'depends': ['oa_integrated', 'galaxy_common'],
    'data': [
        'security/wechat_usergroup.xml',
        'security/wechat_security.xml',
        'security/ir.model.access.csv',
        #'data/ir_actions_server.xml',
        'data/callback_code_data.xml',
        'data/callback_action_data.xml',
        'data/ir_sequence_data.xml',
        #'data/mail_channel_data.xml',
        #'views/res_partner_views.xml',
        'views/wechat_config_views.xml',
        'views/wechat_work_config_views.xml',
        'views/wechat_menu_views.xml',
        #'views/website_wechat_views.xml',
        #'views/wechat_confirm_views.xml',
        #'views/wechat_templates.xml',
        'views/wechat_work_templates.xml',
        'views/wechat_offiaccount_templates.xml',
        'views/wechat_weapp_config_views.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_qweb': [
            'wechat/static/src/xml/sync_button.xml'
        ],
        'web.assets_backend': [
            # TODO: 同步按钮需要重新实现 20231103 'wechat/static/src/js/sync_button_action.js',
        ],
        'web.assets_frontend': [
            'https://rescdn.qqmail.com/node/ww/wwopenmng/js/sso/wwLogin-1.0.0.js',
            'https://res.wx.qq.com/connect/zh_CN/htmledition/js/wxLogin.js',
            # TODO: 同步按钮需要重新实现 20231109 'wechat/static/src/js/wechat_login.js',
            'wechat/static/src/scss/style.scss',
        ],
        'web.assets_frontend_minimal': [
            'wechat/static/src/js/wework.js',
        ],
        'wechat.assets_wechat_frontend': [
            'https://res.wx.qq.com/open/js/jweixin-1.6.0.js'
        ]
    },
}
