# -*- coding: utf-8 -*-
{
    'name': '鸥贝云',
    'version': '2.0',
    'description':
        """
普惠金融产品：鸥贝云
========================

把企业的应收账款转换为信贷产品，并提供相应的账期管理、催收管理，以及配套的法律服务
        """,
    'summary': '企业应收账款管理服务',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Product',
    'sequence': 0,
    'depends': [
        'galaxy_tdesign',
        'ifs_base',
        'ifs_gar_partner_relationship',
        'ifs_gar_risk_manage',
        'ifs_gar_invite',
        'ifs_gar_entry',
        'ifs_gar_review',
        'ifs_gar_contract',
        'ifs_gar_account',
        'ifs_gar_repayment',
        'ifs_partner_autocomplete'
    ],
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/ir_sequence_data.xml',
        # 'data/wechat_offiaccount.xml',
        # 'data/wechat_menu.xml',
        # 'data/offiaccount_taglist.xml',
        # 'views/ifs_prod_gar_menu_views.xml',
        'views/webclient_templates.xml',
        'views/mobile_login_template.xml',
        'views/website_templates.xml',
        'views/s_three_columns.xml',
        'views/s_four_columns.xml',
        'views/s_references.xml',
        'views/s_situation.xml',
        'views/s_solutions.xml',
        'views/s_footer.xml',
        'views/s_management_system.xml',
        'views/snippets.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
        'web.assets_backend': [
            'ifs_prod_gar/static/src/js/gar_service.js',
        ],
        'web.assets_frontend': [
            'ifs_prod_gar/static/src/scss/mobile_login.scss',
            'ifs_prod_gar/static/src/scss/website.scss',
        ],
        'web._assets_primary_variables': [
            ('prepend', 'ifs_prod_gar/static/src/legacy/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('prepend', 'ifs_prod_gar/static/src/legacy/scss/secondary_variables.scss'),
        ],
    }
}