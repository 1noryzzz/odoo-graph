# -*- coding: utf-8 -*-
{
    'name': '审批流程',
    'version': '2.0',
    'description':
        """
鸥贝云审批流程
========================

鸥贝云的供应方、采购方审批流程
        """,
    'summary': '鸥贝云审批流程管理',
    'author': 'Galaxy Team',
    'website': 'https://www.liefwiz.cn',
    'license': 'Other proprietary',
    'category': '鸥贝云/Partner',
    'sequence': 5,
    'depends': [
        'base',
        'mail',
        'galaxy_common',
        'galaxy_tdesign',
        'ifs_gar_partner_relationship',
        'ifs_gar_invite',
        'ifs_gar_entry',
    ],
    'data': [
        'security/ifs_gar_review_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/ifs_gar_entry_supplier_views.xml',
        'views/ifs_gar_entry_merchant_views.xml',
        'views/ifs_gar_entry_franchisee_views.xml',
        'views/ifs_gar_entry_lawfirm_views.xml',
        'views/ifs_partner_merchant_views.xml',
        'wizard/ifs_gar_review_supplier_reject_wizard_views.xml',
        'wizard/ifs_gar_review_franchisee_reject_wizard_views.xml',
        'wizard/ifs_gar_review_lawfirm_reject_wizard_views.xml',
        'wizard/ifs_gar_review_merchant_auditing_wizard_views.xml',
        'wizard/ifs_gar_review_merchant_approve_wizard_views.xml',
        'wizard/ifs_gar_review_merchant_btw_wizard_views.xml',
        'wizard/ifs_gar_review_merchant_reject_wizard_views.xml',
        'entry/ifs_gar_entry_merchant_approval_info_wizard_views.xml',
        'entry/ifs_gar_entry_merchant_btw_info_wizard_views.xml',
        'entry/ifs_gar_entry_merchant_rejected_info_wizard_views.xml',
        'entry/ifs_gar_entry_supplier_reject_info_wizard_views.xml',
        'entry/ifs_gar_entry_franchisee_reject_info_wizard_views.xml',
        'entry/ifs_gar_entry_lawfirm_reject_info_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
