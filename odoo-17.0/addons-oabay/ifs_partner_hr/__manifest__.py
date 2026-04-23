# -*- coding: utf-8 -*-
{
    'name': '合作伙伴员工',
    'version': '2.0',
    'description':
        """
普惠金融合作伙伴各自的员工管理
=================================

合作伙伴各自的员工管理
        """,
    'summary': '合作伙伴的员工管理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Partner',
    'sequence': 22,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_hr',
        'ifs_partner',
    ],
    'data': [
        'security/ifs_partner_hr_security.xml',
        'security/ir.model.access.csv',
        'security/ifs_partner_hr_rules.xml',
        'views/ifs_base_company_views.xml',
        'views/ifs_partner_factor_views.xml',
        'views/ifs_partner_funder_views.xml',
        'views/ifs_partner_insurance_views.xml',
        'views/ifs_partner_insurant_views.xml',
        'views/ifs_partner_insured_views.xml',
        'views/ifs_partner_channelsp_views.xml',
        'views/ifs_partner_supplier_views.xml',
        'views/ifs_partner_merchant_views.xml',
        'wizard/ifs_base_company_root_user_wizard_view.xml',
        'wizard/ifs_partner_factor_root_user_wizard_view.xml',
        'wizard/ifs_partner_funder_root_user_wizard_view.xml',
        'wizard/ifs_partner_insurance_root_user_wizard_view.xml',
        'wizard/ifs_partner_insurant_root_user_wizard_view.xml',
        'wizard/ifs_partner_insured_root_user_wizard_view.xml',
        'wizard/ifs_partner_channelsp_root_user_wizard_view.xml',
        'wizard/ifs_base_company_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_factor_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_funder_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_insurance_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_insurant_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_insured_legal_idcard_wizard_view.xml',
        'wizard/ifs_partner_channelsp_legal_idcard_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        'web.assets_qweb': [
            # 'ifs_template/static/src/webclient/**/*.xml',
        ],
    }
}