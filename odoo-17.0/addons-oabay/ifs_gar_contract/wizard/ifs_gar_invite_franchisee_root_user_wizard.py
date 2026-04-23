# -*- coding: utf-8 -*-
import logging

from odoo import _, api, models, fields
from odoo.exceptions import AccessDenied, UserError

_logger = logging.getLogger(__name__)


class GuaranteeAccountsRecInviteFraRootUserWizard(models.TransientModel):
    _inherit = 'ifs.gar.invite.franchisee.root.user.wizard'

    def action_confirm(self):
        if self.ifs_company_id.id:
            if 'factor' in (self.env.company.ifs_partners or []):
                invite_franchisee = self.env['ifs.gar.invite.franchisee'].search([
                    ('ifs_company_id', '=', self.ifs_company_id.id),
                    ('factor_id.company_id', '=', self.env.company.id)
                ], limit=1)
                if invite_franchisee.id:
                    if invite_franchisee.p01_contract_info_id.id:
                        return super().action_confirm()
                    else:
                        raise UserError(_('合同还没准备好，不能发出邀请。请先预览合同！'))
                else:
                    raise UserError(_('数据错误！'))
            else:
                raise AccessDenied(_('仅保理方可以发出邀请'))
        else:
            raise AccessDenied(_('数据错误！'))
