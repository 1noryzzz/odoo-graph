# -*- coding: utf-8 -*-

import asyncio
import logging

from odoo import _, api, models, fields
from dateutil.relativedelta import relativedelta
from functools import reduce

_logger = logging.getLogger(__name__)

class InclusiveFinancingBaseCompany(models.Model):
    _inherit = 'ifs.base.company'

    # 标识当前公司是否需要抓取更多信息，用于对其进行风险控制
    need_fetch = fields.Boolean('是否需要抓取更多信息', default=False, copy=False)
    last_fetch_time = fields.Datetime('最后抓取时间', copy=False)

    last_risk_credit_id = fields.Many2one('ifs.risk.manage.credits', string='最后一份法人征信报告')
    last_guarantor_risk_credit_id = fields.Many2one('ifs.risk.manage.credits', string='最后一份担保人征信报告')
    last_fetch_credit_time = fields.Datetime('最后抓取法人及负责人的个人征信信息时间', copy=False)
    last_fetch_pd_credit_time = fields.Datetime('最后抓取法人及负责人的个人朴道征信信息时间', copy=False)

    shareholder_ids = fields.One2many(
        'ifs.base.company.shareholder', 'ifs_company_id', string='股东')
    shareholder_count = fields.Integer(
        '股东数量', compute='_compute_shareholder_branch_count')

    branch_ids = fields.One2many(
        'ifs.base.company.branch', 'ifs_company_id', string='分支机构/对外投资')
    branch_count = fields.Integer(
        '分支机构数量', compute='_compute_shareholder_branch_count')

    def _compute_shareholder_ids(self):
        for company in self:
            # 股东
            stock_reqs = self.env['galaxy.external.api'].invoke('TYC-QYGD', query={
                'keyword': self.company_registry,
            }).retrieve_response('STOCK', False)
            shareholders = stock_reqs and [
                stock_req.raw for stock_req in stock_reqs]
            if shareholders:
                delete_shareholder_list = company.shareholder_ids.filtered(
                    lambda f: f.name not in [shareholder.get('name') for shareholder in shareholders])
                insert_shareholder_list = list(filter(lambda s: s.get('name') not in [
                    shareholder_id.name for shareholder_id in company.shareholder_ids], shareholders))
                update_shareholder_list = list(filter(lambda s: s.get(
                    'name') not in [insert.get('name') for insert in insert_shareholder_list], shareholders))

                final_shareholder_list = []
                for insert_shareholder in insert_shareholder_list:
                    if insert_shareholder.get('type') == 1:
                        shareholder_info = self.env['ifs.base.company'].sync_business_registration(
                            {'name': insert_shareholder.get('name')})
                    subscribed_ratio = float(insert_shareholder.get('capital')[0].get('percent').replace(
                        '%', ''))/100 if insert_shareholder.get('capital') and insert_shareholder.get('capital')[0].get('percent') else 0
                    paid_in_ratio = float(insert_shareholder.get('capitalActl')[0].get('percent').replace('%', ''))/100 if insert_shareholder.get(
                        'capitalActl') and insert_shareholder.get('capitalActl')[0].get('percent') else 0
                    param = {
                        'name': insert_shareholder.get('name'),
                        'subscribed_capital': insert_shareholder.get('capital') and insert_shareholder.get('capital')[0].get('amomon'),
                        'paid_in_capital': insert_shareholder.get('capitalActl') and insert_shareholder.get('capitalActl')[0].get('amomon'),
                        'subscribed_ratio': subscribed_ratio,
                        'paid_in_ratio': paid_in_ratio,
                        'type':str(insert_shareholder.get('type'))
                    }
                    final_shareholder_list += [
                        fields.Command.create(param)]
                final_shareholder_list += [fields.Command.update(company.shareholder_ids.filtered(
                    lambda r: r.name == update_shareholder.get('name')).id, {
                        'name': update_shareholder.get('name'),
                        'subscribed_capital': update_shareholder.get('capital') and update_shareholder.get('capital')[0].get('amomon'),
                        'paid_in_capital': update_shareholder.get('capitalActl') and update_shareholder.get('capitalActl')[0].get('amomon'),
                        'subscribed_ratio': float(update_shareholder.get('capital')[0].get('percent').replace(
                            '%', ''))/100 if update_shareholder.get('capital') and update_shareholder.get('capital')[0].get('percent') else 0,
                        'paid_in_ratio': float(update_shareholder.get('capitalActl')[0].get('percent').replace('%', ''))/100 if update_shareholder.get(
                            'capitalActl') and update_shareholder.get('capitalActl')[0].get('percent') else 0,
                        'type':str(update_shareholder.get('type'))
                }) for update_shareholder in update_shareholder_list]
                delete_shareholder_list.unlink()
                company.write({
                    'shareholder_ids': final_shareholder_list
                })

    def _compute_branch_ids(self):
        for company in self:
            # 分支机构
            branch_reqs = self.env['galaxy.external.api'].invoke('TYC-FZJG', query={
                'keyword': self.company_registry,
            }).retrieve_response('HQQYFZJGXX', False)
            branchs = branch_reqs and [
                branch_req.raw for branch_req in branch_reqs]
            if branchs:
                delete_branch_list = company.branch_ids.filtered(
                    lambda f: f.name not in [branch.get('name') for branch in branchs] and f.is_investment == False)
                insert_branch_list = list(filter(lambda s: s.get(
                    'name') not in [branch.name for branch in company.branch_ids], branchs))
                update_branch_list = list(filter(lambda s: s.get('name') not in [
                    insert.get('name') for insert in insert_branch_list], branchs))

                for insert_branch in insert_branch_list:
                    if '注销' not in insert_branch.get('regStatus') and '吊销' not in insert_branch.get('regStatus'):
                        branch_info = self.env['ifs.base.company'].sync_business_registration(
                            {'company_registry': insert_branch.get('name')})
                        company.branch_ids = [fields.Command.create({
                            'share_ratio': float(insert_branch.get('percent').replace('%', ''))/100 if insert_branch.get('percent') and insert_branch.get('percent') != '-' else 1,
                            'branch_id': branch_info.id,
                            'is_investment': True if insert_branch.get('creditCode') else False
                        })]
                company.branch_ids = [fields.Command.update(company.branch_ids.filtered(lambda r: r.name == update_branch.get('name')).id, {
                    'share_ratio': float(update_branch.get('percent').replace('%', ''))/100 if update_branch.get('percent') and update_branch.get('percent') != '-' else 1,
                }) for update_branch in update_branch_list]
                delete_branch_list.unlink()

            # 对外投资
            invest_reqs = self.env['galaxy.external.api'].invoke('TYC-DWTZ', query={
                'keyword': self.company_registry,
            }).retrieve_response('HQQYDWTZXX', False)
            invests = invest_reqs and [
                invest_req.raw for invest_req in invest_reqs]
            if invests:
                delete_invest_list = company.branch_ids.filtered(
                    lambda f: f.name not in [invest.get('name') for invest in invests] and f.is_investment == True)
                insert_invest_list = list(filter(lambda s: s.get(
                    'name') not in [branch.name for branch in company.branch_ids], invests))

                for insert_invest in insert_invest_list:
                    if '注销' not in insert_invest.get('regStatus') and '吊销' not in insert_invest.get('regStatus'):
                        invest_info = self.env['ifs.base.company'].sync_business_registration(
                            {'company_registry': insert_invest.get('name')})
                        company.branch_ids = [fields.Command.create({
                            'branch_id': invest_info.id,
                            'is_investment': True if insert_invest.get('creditCode') else False
                        })]
                delete_invest_list.unlink()

    @api.depends('shareholder_ids', 'branch_ids')
    def _compute_shareholder_branch_count(self):
        for company in self:
            company.update({
                'shareholder_count': len(company.shareholder_ids) if company.shareholder_ids else 0,
                'branch_count': len(company.branch_ids) if company.branch_ids else 0,
            })

    def _next_fetch_date(self, sync_frequency):
        next_date = False
        if sync_frequency == 'monthly':
            next_date = fields.Datetime.now() + relativedelta(months=-1)
        elif sync_frequency == 'weekly':
            next_date = fields.Datetime.now() + relativedelta(weeks=-1)
        elif sync_frequency == 'daily':
            next_date = fields.Datetime.now() + relativedelta(days=-1)

        return next_date

    async def _fetch_company_info(self, api_codes):
        for api_code in api_codes:
            req = self.env['galaxy.external.api'].invoke(api_code, query={
                'keyword': self.company_registry,
            })
            clear_detail_codes = req.response_codes or req.response_ids.mapped(
                'code')
            update_detail_ids = {
                'detail_ids': [fields.Command.create({
                    'code': rdata.code,
                    'definition_id': rdata.definition_id.id,
                    'raw': rdata.raw,
                }) for rdata in req.response_ids] + ([fields.Command.delete(
                    old_id) for old_id in self.detail_ids.filtered(
                        lambda x: x.code in clear_detail_codes).ids]),
                'last_fetch_time': fields.Datetime.now()
            }
            self.write(update_detail_ids)
        self._compute_shareholder_ids()
        self._compute_branch_ids()

    async def _fetch_all(self, api_codes):
        Config = self.env['ir.config_parameter'].sudo()
        sync_frequency = Config.get_param(
            'ifs_base.business_registration_update_frequency', 'monthly')

        will_fetct_ifs_companies = self.search(
            [('need_fetch', '=', True), '|', ('last_fetch_time', '=', False), ('last_fetch_time', '<', self._next_fetch_date(sync_frequency))])
        tasks = []
        for ifs_company in will_fetct_ifs_companies:
            try:
                task = asyncio.create_task(ifs_company._fetch_company_info(api_codes))
                tasks.append(task)
            except Exception as e:
                _logger.error(repr(e))
                continue
        await asyncio.gather(*tasks)

    def start_fetch(self, api_codes):
        asyncio.run(self._fetch_all(api_codes))
