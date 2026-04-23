# -*- coding: utf-8 -*-

{
    'name': '鸥贝云风险管控',
    'version': '2.0',
    'description':
        """
鸥贝云产品的风险管控模块
========================

调用百融征信获取征信报告
        """,
    'summary': '鸥贝云产品的风险管控模块',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/RiskManager',
    'sequence': 3,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_partner',
        'ifs_partner_risk_manage',
        'ifs_gar_partner_relationship',
    ],
    'data': [
        'security/ifs_gar_risk_manage_security.xml',
        # 'security/ir.model.access.csv',
        'views/ifs_partner_merchant_business_credits_views.xml',
        'views/ifs_partner_merchant_business_views.xml',
        # 'views/ifs_partner_merchant_credits_views.xml',
        # 'views/ifs_partner_supplier_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}