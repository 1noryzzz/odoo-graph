# -*- coding: utf-8 -*-
{
    "name": "前端API",
    "version": "2.0",
    "description": """
青钱闪付API入口
        """,
    "summary": "青钱闪付API",
    "author": "Galaxy Team",
    "website": "https://cloud.oabay.com",
    "license": "Other proprietary",
    "category": "GalaxyBase/QingQianAPI",
    "sequence": 99,
    "depends": [
        "base",
        "mail",
        "galaxy_common",
        "galaxy_external_api",
        "web",
        "website",
        "wechat",
        "galaxy_aliyun",
    ],
    "data": [
        "security/galaxy_qq_api_security.xml",
        "security/ir.model.access.csv",
        "data/sms_template_setting.xml",
        "data/qq_login_email_templates.xml",
        "data/ir_cron_ipinfo.xml",
        "views/galaxy_qq_api_menu_views.xml",
        "views/galaxy_qq_api_views.xml",
        "views/galaxy_qq_api_templates.xml",
        'views/res_config_settings_views.xml',
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "assets": {},
}
