# -*- coding: utf-8 -*-
{
    'name': '合作伙伴合同管理',
    'version': '2.0',
    'description':
        """
普惠金融场景下，各合作伙伴自己的合同管理权限集
========================

给合作伙伴员工授权合同相应的权限
        """,
    'summary': '各合作伙伴的合同管理权限集',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': 'InclusiveFinancing/Base',
    'sequence': 24,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_contract',
        'ifs_partner',
        'ifs_partner_hr',
    ],
    'data': [
        'security/ifs_partner_contract_security.xml',
        'security/ifs_partner_contract_rules.xml',
        'security/ir.model.access.csv',
        'views/ifs_contract_template_views.xml',
        'wizard/ifs_contract_template_supplier_selector_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}