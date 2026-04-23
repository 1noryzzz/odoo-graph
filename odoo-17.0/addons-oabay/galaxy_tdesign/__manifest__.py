# -*- coding: utf-8 -*-
{
    'name': '界面风格之TDesign',
    'version': '17.0.1.0',
    'description':
        """
云腾通用主题
========================
按TDesign的风格做的主题
        """,
    'summary': '界面风格',
    'author': 'Ferren Liu',
    'company': 'Galaxy',
    'maintainer': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'GalaxyBase/Themes',
    'depends': ['base', 'web', 'galaxy_common', 'portal'],
    'data': [
        'views/website_templates.xml',
        'views/webclient_templates.xml',
        'views/mobile_portal_template.xml',
        'views/signature_template.xml',
        'views/res_config_settings_views.xml',
        'views/res_users.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'galaxy_tdesign.assets_login_frontend': [
            'galaxy_tdesign/static/src/scss/login.scss',
        ],
        'web._assets_primary_variables': [
            ('prepend', 'galaxy_tdesign/static/src/scss/primary_variables.scss'),
            ('before', 'web/static/src/webclient/navbar/navbar.variables.scss', 'galaxy_tdesign/static/src/webclient/navbar/navbar.variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('prepend', 'galaxy_tdesign/static/src/scss/secondary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('prepend', 'galaxy_tdesign/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'galaxy_tdesign/static/src/webclient/navbar/navbar.scss',
            'galaxy_tdesign/static/src/scss/sign.scss',
            'galaxy_tdesign/static/src/js/galaxy_signature.js',
            'galaxy_tdesign/static/src/xml/galaxy_signature.xml',
            'galaxy_tdesign/static/src/js/mobile_signature.js',
            'galaxy_tdesign/static/src/xml/mobile_signature.xml',
            'galaxy_tdesign/static/src/js/jweixin-1.4.0.js',
            'galaxy_tdesign/static/src/js/uni-webview.js',
            'galaxy_tdesign/static/src/scss/modify_password.scss',
        ],
        'web.assets_backend': [
            ('prepend', 'galaxy_tdesign/static/src/views/form/form.variables.scss'),
            'galaxy_tdesign/static/src/core/**/*',
            # TODO: 这个平铺样式需要重新实现 20231103 'galaxy_tdesign/static/src/search/**/*',
            'galaxy_tdesign/static/src/views/**/*',
            ('remove', 'galaxy_tdesign/static/src/views/kanban/flat_kanban.js'), 
            ('remove', 'galaxy_tdesign/static/src/views/list/flat_tree.js'), 
            'galaxy_tdesign/static/src/webclient/**/*',
            'galaxy_tdesign/static/src/scss/galaxy_form.scss',
            'galaxy_tdesign/static/src/scss/galaxy_kanban.scss',
            'galaxy_tdesign/static/src/scss/ifs_gar_partner.scss',
        ]
    },
}
