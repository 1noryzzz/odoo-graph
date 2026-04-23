# -*- coding: utf-8 -*-
{
    'name': '金融业务合作伙伴',
    'version': '2.0',
    'description':
        """
普惠金融合作伙伴
========================

金融业务下的各合作伙伴
        """,
    'summary': '金融业务合作伙伴模块',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Partner',
    'sequence': 12,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'galaxy_open_api',
        'ifs_base',
        'ifs_partner_autocomplete',
    ],
    'data': [
        'security/ifs_partner_security.xml',
        'security/ifs_partner_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ifs_base_company_actions_server_data.xml',
        'views/galaxy_open_api_app_views.xml',
        'views/ifs_base_company_views.xml',
        'views/ifs_partner_factor_views.xml',
        'views/ifs_partner_franchisee_views.xml',
        'views/ifs_partner_lawfirm_views.xml',
        'views/ifs_partner_funder_views.xml',
        'views/ifs_partner_merchant_views.xml',
        'views/ifs_partner_supplier_views.xml',
        'views/ifs_partner_insurance_views.xml',
        'views/ifs_partner_insurant_views.xml',
        'views/ifs_partner_insured_views.xml',
        'views/ifs_partner_channelsp_views.xml',
        'views/res_bank_views.xml',
        'views/ifs_partner_menu_views.xml',
        'wizard/ifs_partner_factor_wizard_views.xml',
        'wizard/ifs_partner_factor_bank_wizard_views.xml',
        'wizard/ifs_partner_factor_contact_wizard_views.xml',
        'wizard/ifs_partner_factor_business_license_wizard_views.xml',
        'wizard/ifs_partner_funder_wizard_views.xml',
        'wizard/ifs_partner_funder_bank_wizard_views.xml',
        'wizard/ifs_partner_funder_contact_wizard_views.xml',
        'wizard/ifs_partner_funder_business_license_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'ifs_partner/static/src/views/**/*',
            'ifs_partner/static/src/scss/ifs_partner.scss',
            'ifs_partner/static/src/legacy/scss/form_view.scss',
        ]
    }
}
