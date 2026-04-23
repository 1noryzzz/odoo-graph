# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WeappConfig(models.Model):
    _name = 'wechat.weapp.config'
    _description = 'Weapp Config'
    _inherit = ['wechat.config.mixin', 'mail.thread',
                'mail.activity.mixin', 'image.mixin']

    def _default_effective_pricelist_id(self, company_id):
        return self.env['product.pricelist'].search([
            '|', ('company_id', '=', False),
            ('company_id', '=', company_id)], order='company_id', limit=1)

    weapp_user_ids = fields.One2many(
        'wechat.weapp.user', 'weapp_id', string='Weapp Users')

    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', index=True, ondelete='set null')
    effective_pricelist_id = fields.Many2one(
        'product.pricelist', 'Effective Pricelist', compute="_compute_effective_pricelist_id")

    @api.depends('pricelist_id')
    def _compute_effective_pricelist_id(self):
        for weapp_config in self:
            if not weapp_config.pricelist_id:
                weapp_config.effective_pricelist_id = self._default_effective_pricelist_id(
                    weapp_config.website_id.company_id.id)
            else:
                weapp_config.effective_pricelist_id = weapp_config.pricelist_id

    @api.constrains('website_id', 'is_default')
    def _check_only_one_default(self):
        """ Do not allow one website with two default weapp config """
        self.flush_recordset(['website_id', 'is_default'])
        self.env.cr.execute(
            """SELECT website_id
                 FROM wechat_weapp_config
                WHERE website_id IN (select website_id from wechat_weapp_config where id IN %s AND is_default=true) 
                 AND is_default=true 
             GROUP BY website_id
               HAVING COUNT(*) > 1
            """,
            (tuple(self.ids),)
        )
        if self.env.cr.rowcount:
            raise ValidationError(
                _("A website only can has one default config."))

    def retrieve_entry(self, app_id=None, website_id=None):
        from ..rpc import weapp_entry

        if app_id:
            wechat_weapp = self.search([('app_id', '=', app_id)])
        elif website_id:
            wechat_weapp = self.search(
                [('website_id', '=', website_id), ('is_default', '=', True)], limit=1)
        else:
            wechat_weapp = self.search(
                [('is_default', '=', True)], limit=1)
        return wechat_weapp, weapp_entry.retrieve_entry(self.env, wechat_weapp.app_id)
