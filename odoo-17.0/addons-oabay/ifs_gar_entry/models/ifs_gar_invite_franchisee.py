# -*- coding: utf-8 -*-

from odoo import _, api, models, fields, Command
from odoo.exceptions import AccessDenied


class GuaranteeAccountsRecInviteFranchisee(models.Model):
    _inherit = 'ifs.gar.invite.franchisee'

    entry_ids = fields.One2many(
        'ifs.gar.entry.franchisee', 'invite_id', string='进件流程s', copy=False)
    entry_id = fields.Many2one(
        'ifs.gar.entry.franchisee', string='进件流程', compute='_compute_entry_id', copy=False)
    entry_date = fields.Datetime('进件时间', copy=False)
    
    franchisee_id = fields.Many2one(
        'ifs.partner.franchisee',
        string='事业合伙人', index=True, ondelete='set null', help='邀请成功进件，成功加入后的事业合伙人')
    franchisee_code = fields.Char('事业合伙人编号', related='franchisee_id.seq_code')

    def start_entry_portal(self):
        if not self.entry_id:
            self.write({
                'state': 'waiting',
                'entry_ids': [Command.create({
                    'ifs_company_id': self.ifs_company_id.id,
                    'state': 'draft',
                })]
            })
            
    @api.depends('entry_ids')
    def _compute_entry_id(self):
        for invite in self:
            invite.entry_id = invite.entry_ids[0] if invite.entry_ids else False

    def write(self, vals):
        if 'state' in vals and vals.get('state') == 'activation' and not self.entry_date:
            vals['entry_date'] = fields.Datetime.now()
        elif 'state' in vals and vals.get('state') == 'ready':
            entry_pass = True
            waiting_list = self.sudo().search([
                ('ifs_company_id', '=', self.ifs_company_id.id),
                ('id', '!=', self.id),
                ('state', '!=', 'ready')])
            if waiting_list.exists():
                # 如果还有其它的邀请未处理完成，则仅开通，暂不去掉进件权限组
                entry_pass = False
            self.ifs_company_id.with_context(
                entry_pass=entry_pass).active_ifs_partner(self._invite_ifs_partner)
        return super().write(vals)
    
    def view_invite(self):
        if self.entry_id and 'factor' in (self.env.company.ifs_partners or []):
            return self.entry_id.view_invite()
        return {
            'name': self._description,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'target': 'current',
        }

    def start_entry(self):
        waiting_list = self.filtered(lambda r: r.state != 'ready')
        if not waiting_list or len(waiting_list) == 0:
            # TODO: 跳转到公司信息页面
            raise AccessDenied(_('当前未收到进件邀请或已经完成进件！'))
        elif len(waiting_list) == 1:
            if waiting_list.state in ['draft', 'sended']:
                if waiting_list.entry_ids:
                    raise AccessDenied(_('当前合伙人已经进件！'))

                waiting_list.write({
                    'state': 'waiting',
                    'entry_ids': [Command.create({
                        'ifs_company_id': waiting_list.ifs_company_id.id,
                        'state': 'draft',
                    })]
                })

                return waiting_list.entry_id.start_step()
            elif waiting_list.state in ['waiting']:
                entry_list = waiting_list.entry_ids.filtered(
                    lambda entry: entry.state in ['draft', 'rejected'])
                if entry_list.exists():
                    return entry_list[0].start_step()
                else:
                    raise AccessDenied(_('进件数据错误，请联系管理员！'))
            elif waiting_list.state in ['activation']:
                entry_list = waiting_list.entry_ids.filtered(
                    lambda entry: entry.state == 'committed')
                if entry_list.exists() and len(entry_list) == 1:
                    return entry_list.start_step()
                else:
                    raise AccessDenied(_('进件数据错误，请联系管理员！'))
            else:
                raise AccessDenied(_('当前状态不允许进件！'))
        else:
            return {
                'name': _('选择保理方'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'ifs.gar.entry.factor.selector.wizard',
                'res_id': False,
                'target': 'new',
                'context': {
                    'invite_ifs_partner': self._invite_ifs_partner
                },
            }
