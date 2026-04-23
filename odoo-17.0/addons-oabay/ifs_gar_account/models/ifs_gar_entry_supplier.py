# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import _, api, models, fields, Command


class GuaranteeAccountsRecEntrySupplier(models.Model):
    _inherit = 'ifs.gar.entry.supplier'

    total_quota = fields.Monetary('合作额度', required=True, default=10000000.00)

    def _utc_cut_off_time(self, cut_off_time):
        cut_off_datetime = datetime.utcfromtimestamp((
            fields.Datetime.context_timestamp(self, fields.Datetime.today())
            .replace(hour=0, minute=0, second=0) + timedelta(hours=cut_off_time)).timestamp())

        if cut_off_datetime <= fields.Datetime.today():
            cut_off_datetime += timedelta(days=1)
        return cut_off_datetime

    def _create_cut_off_cron(self):
        cron_name = '保理账单日切定时任务（供应方编号：%s）' % self.supplier_id.seq_code
        cut_time = self._utc_cut_off_time(self.invite_id.cut_off_time)
        model_id = self.env.ref(
            'ifs_gar_account.model_ifs_gar_sub_loan_account').id
        user = self.env.ref('ifs_gar_account.ifs_gar_account_user_id')
        company = self.supplier_id.ifs_company_id.company_id if self.supplier_id.ifs_company_id else None
        if company and company not in user.company_ids:
            user.sudo().write({'company_ids': [Command.link(company.id)]})
        user_id = user.id

        exist_cron = self.env['ir.cron'].sudo().search([
            ('name', '=', cron_name),
            ('model_id', '=', model_id),
            ('nextcall', '=', cut_time),
            ('user_id', '=', user_id),
        ], limit=1)
        if exist_cron.exists():
            return exist_cron.id
        else:
            return self.env['ir.cron'].sudo().create({
                'name': cron_name,
                'model_id': model_id,
                'state': 'code',
                'user_id': user_id,
                'code': '''
accounts = model.search([('state', '!=', 'draft'), ('supplier_id.seq_code', '=', '%s')])
if accounts.exists():
    for account in accounts:
        account.daliy_cut_off()
                    ''' % self.supplier_id.seq_code,
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': -1,
                'nextcall': cut_time,
                'doall': False,
            }).id

    def action_approve(self):
        super().action_approve()

        factor_supplier = self.env['ifs.gar.partner.factor.supplier'].search([
            ('entry_id', '=', self.id)], limit=1)
        factor_supplier.write({
            'cut_off_time': self.invite_id.cut_off_time,
            'cut_off_cron_id': self._create_cut_off_cron(),
            'fee_solution_id': self.invite_id.fee_solution_id.id,
            'total_quota': self.total_quota,
        })
