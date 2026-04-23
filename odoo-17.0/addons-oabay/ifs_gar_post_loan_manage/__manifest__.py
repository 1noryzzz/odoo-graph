# -*- coding: utf-8 -*-

{
    "name": "贷后管理",
    "version": "2.0",
    "description": """
        贷后管理
        =============================================
        催收管理、贷后流程管理
    """,
    "summary": "贷后管理与催收管理",
    "author": "Haonan Li",
    "website": "https://www.oabay.com",
    "license": "Other proprietary",
    "category": "鸥贝云/PostLoan",
    "sequence": 12,
    "depends": ["base", "ifs_gar_account", "ifs_gar_contract", "ifs_contract"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/ifs_gar_collection_order_views.xml",
        "views/ifs_gar_post_loan_manage_menu_views.xml",
        "data/t24_contract_template.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
