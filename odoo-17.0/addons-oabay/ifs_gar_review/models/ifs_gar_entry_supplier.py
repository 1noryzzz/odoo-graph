# -*- coding: utf-8 -*-

from odoo import _, api, models, fields, Command


class GuaranteeAccountsRecEntrySupplier(models.Model):
    _inherit = 'ifs.gar.entry.supplier'

    review_date = fields.Datetime('审批时间', copy=False)
    reject_reason = fields.Html('驳回原因', copy=False)
    
    can_confirm = fields.Boolean('可确认', compute="_compute_can_confirm")
    
    @api.depends('state')
    def _compute_can_confirm(self):
        for record in self:
            record.can_confirm = (
                record.factor_id.company_id.id == self.env.company.id and
                record.state == 'committed')

    def write(self, vals):
        if 'state' in vals and vals.get('state') in ['rejected', 'approval'] and not self.review_date:
            vals['review_date'] = fields.Datetime.now()
        return super().write(vals)

    def start_step(self):
        if self.state == 'rejected':
            first_model = 'ifs.gar.entry.supplier.reject.info.wizard'
            return {
                'name': self.env[first_model]._description,
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': first_model,
                'res_id': False,
                'target': 'current',
                'context': {
                    f'default_{self._ref_id_field}': self.id,
                }
            }
        return super().start_step()

    def action_approve(self):
        self.ensure_one()

        if self.can_confirm:
            partner_bank_info = {
                'bank_id': self.bank_id.id,
                'acc_number': self.acc_number,
                'currency_id': self.company_id.currency_id.id,
            }

            partner = self.env['res.partner'].search([
                ('parent_id', '=', self.partner_id.id),
                ('name', '=', self.finance_name)])
            if not partner.exists():
                partner = self.env['res.partner'].create({
                    'name': self.finance_name,
                    'phone': self.finance_phone,
                    'mobile': self.finance_phone,
                    'parent_id': self.partner_id.id
                })

            # 把进件向导录入的信息更新到当前进件的公司全局信息中
            self.ifs_company_id.write({
                'finance_id': partner.id,
                'phone': self.phone,
                'email': self.email,
                'business_address': self.business_address,
                'business_license': self.business_license,
                'deposit_license': self.deposit_license,
                'bank_ids': [Command.update(self.ifs_company_id.acquiescence_bank_id.id, partner_bank_info)] if self.ifs_company_id.acquiescence_bank_id else [Command.create(partner_bank_info)],
                'reception_picture': self.reception_picture,
                'office_area_picture': self.office_area_picture,
            })

            factor_supplier_data = {
                'entry_id': self.id,
                'factor_id': self.factor_id.id,
                'franchisee_id': self.franchisee_id.id if self.franchisee_id else False,
                'product_scope': self.product_scope,
            }
            partner_supplier_sudo = self.env['ifs.partner.supplier'].sudo()
            supplier = partner_supplier_sudo.search([
                ('ifs_company_id', '=', self.ifs_company_id.id)], limit=1)
            if not supplier.exists():
                supplier = partner_supplier_sudo.create({
                    'ifs_company_id': self.ifs_company_id.id,
                })

            factor_supplier_data.update({
                'supplier_id': supplier.id,
            })
            self.env['ifs.gar.partner.factor.supplier'].create(
                factor_supplier_data)

            # 更新法人信息
            idcard = self.env['hr.employee.idcard'].sudo(
            ).create_legal_from_entry(self)
            self.root_employee_id.sudo().write({
                'gender': idcard.gender,
                'birthday': idcard.birthday,
                'idcard_id': idcard.id,
            })

            self.write({
                'state': 'approval',
                'supplier_id': supplier.id,
            })

    def action_reject(self):
        if self.can_confirm:
            return {
                'name': '供应方进件审批驳回向导',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.review.supplier.reject.wizard',
                'target': 'new',
                'context': {
                    'default_entry_id': self.id,
                }
            }
