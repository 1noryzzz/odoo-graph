# -*- coding: utf-8 -*-
{
    'name': '员工管理',
    'version': '2.0',
    'description':
        """
普惠金融场景下的员工管理
====================================
为员工管理增加金融场景下需要的信息
        """,
    'summary': '金融场景下的员工管理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Hr',
    'sequence': 13,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_aliyun',
        'one_time_password',
        'hr',
        'ifs_base',
        'ifs_wechat',
    ],
    'data': [
        'security/ifs_hr_security.xml',
        'security/ifs_work_position_rules.xml',
        'security/ir.model.access.csv',
        'data/sms_template_setting.xml',
        'views/ifs_hr_menu_views.xml',
        'views/ifs_work_position_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/reset_password_templates.xml',
        'views/webclient_templates.xml',
        'wizard/idcard_uploader_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
        'ifs_hr.assets_for_login': [
            'ifs_hr/static/src/scss/ifs_hr.scss',
        ],
        'web.assets_frontend': [
            # TODO: 230010----------employee_login.js暂时挪到这里，放在'ifs_hr.assets_for_login'会报错：
            # The following modules are needed by other modules but have not been defined, they may not be present in the correct asset bundle:@web/legacy/js/public/public_widget
            'ifs_hr/static/src/js/employee_login.js',
            'ifs_hr/static/src/js/reset_password.js',
        ],
        'web.assets_backend': [
            'ifs_hr/static/src/scss/ifs_hr.scss',
        ]
    }
}