# -*- coding: utf-8 -*-

import os
import sys

#from . import report

sys.path.append(os.path.join(os.path.abspath(
    os.path.join(os.path.dirname(__file__))), 'external_libs/wechatpy'))

from odoo import SUPERUSER_ID, api
from . import controllers, models, wizard

def uninstall_hook(cr, registry):

    env = api.Environment(cr, SUPERUSER_ID, {})
    # pl_rule = env.ref('product.product_pricelist_comp_rule',
    #                  raise_if_not_found=False)
    # pl_item_rule = env.ref(
    #    'product.product_pricelist_item_comp_rule', raise_if_not_found=False)
    #multi_company_rules = pl_rule or env['ir.rule']
    #multi_company_rules += pl_item_rule or env['ir.rule']
    #multi_company_rules.write({'active': True})
