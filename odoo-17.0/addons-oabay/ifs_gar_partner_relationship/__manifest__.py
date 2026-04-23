# -*- coding: utf-8 -*-

{
    'name': '鸥贝云客户关系',
    'version': '2.0',
    'description':
        """
鸥贝云产品的合作伙伴关系图谱
========================

支撑鸥贝云业务的合作伙伴关系
        """,
    'summary': '合作伙伴之间的关联关系',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Partner',
    'sequence': 1,
    'depends': [
        'ifs_partner',
        'ifs_partner_hr',
        'ifs_risk_manage'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ifs_gar_partner_relationship_rules.xml',
        'views/ifs_gar_partner_relationship_menu_views.xml',
        'views/ifs_base_company_views.xml',
        'views/ifs_partner_factor_views.xml',
        'views/ifs_partner_merchant_views.xml',
        'views/ifs_partner_merchant_sign_template.xml',
        'views/ifs_partner_supplier_views.xml',
        'views/ifs_partner_franchisee_views.xml',
        'views/ifs_partner_lawfirm_views.xml',
        'views/ifs_partner_factor_sign_template.xml',
        'wizard/ifs_partner_factor_sign_wizard_views.xml',
        'views/ifs_partner_funder_views.xml',
        'views/ifs_partner_funder_sign_template.xml',
        'wizard/ifs_partner_funder_sign_wizard_views.xml',
        'views/ifs_partner_supplier_sign_template.xml',
        'wizard/ifs_partner_supplier_sign_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {

    }
}
