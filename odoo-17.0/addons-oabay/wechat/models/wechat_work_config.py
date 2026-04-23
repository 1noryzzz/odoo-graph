# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class WorkConfig(models.Model):
    _name = 'wechat.work.config'
    _description = '企业微信账号配置'
    _inherits = {'res.company': 'company_id'}
    _order = 'name'

    corp_id = fields.Char('CorpId', required=True)
    corp_contact_secret = fields.Char('通讯录同步Secret', required=True)
    external_contact_secret = fields.Char('外部联系人同步Secret')
    company_id = fields.Many2one(
        "res.company", string=u'公司名称', index=True, ondelete="restrict", auto_join=True, required=True)
    agent_ids = fields.One2many(
        'wechat.work.agent.config', 'work_id', string='应用配置')
    default_agent_id = fields.Char(
        '默认AgentId', compute="_compute_default_agent_id")
    work_user_ids = fields.One2many(
        'wechat.work.user', 'work_id', string='企业用户')

    _sql_constraints = [
        ('company_id_uniq', 'UNIQUE (company_id)', '一个公司仅可配置一个企业微信账号'),
    ]

    def retrieve_entry(self, company_id=None, corp_id=None):
        from ..rpc import work_entry

        if not company_id:
            company_id = self.env.company.id

        if corp_id:
            wechat_work = self.search([('corp_id', '=', corp_id)])
        else:
            wechat_work = self.search([('company_id', '=', company_id)])
        return wechat_work, work_entry.retrieve_entry(self.env, wechat_work.corp_id)

    @api.depends('agent_ids')
    def _compute_default_agent_id(self):
        for wechat_work in self:
            wechat_work.default_agent_id = None
            if len(wechat_work.agent_ids.ids) > 0:
                agents = wechat_work.agent_ids.filtered(
                    lambda line: (line.qr_login_id and line.qr_login_id.enabled))
                if agents.exists():
                    wechat_work.default_agent_id = agents[0].agent_id

    def wechat_work_sync(self):
        from ..rpc import work_entry

        self.ensure_one()
        entry = work_entry.retrieve_entry(self.env, self.corp_id)

        try:
            update_count = self.agent_ids.wechat_work_sync(entry)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _(u'同步成功'),
                    'message': u'总共同步 %d 个应用' % update_count,
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload_context'
                    }
                },
            }
        except Exception as e:
            raise UserError(e)


class WorkAgentConfig(models.Model):
    _name = 'wechat.work.agent.config'
    _description = '企业微信应用配置'
    _inherit = ['qr.login.provider.mixin',
                'mail.thread', 'mail.activity.mixin']
    _order = 'qr_login_id, name'

    name = fields.Char('应用名称', required=True)
    agent_id = fields.Char('AgentId', required=True)
    agent_secret = fields.Char('Agent Secret', required=True)
    work_id = fields.Many2one(
        "wechat.work.config", u'企业微信账号', required=True,
        index=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one(string=u"所属公司",
                                 related='work_id.company_id', store=True, index=True)
    remark = fields.Text('应用简介')
    #is_default = fields.Boolean("Is Default", default=False)
    message_handler_url = fields.Char(
        '事件处理URL', readonly=True, compute='_compute_message_handler_url')
    message_token = fields.Char(u'签名 token')
    message_encoding_aeskey = fields.Char(u'加密 aes_key')

    icon_url = fields.Html(string=u'应用图标', compute='_compute_icon_url')
    icon_avatar_url = fields.Text(string=u'应用图标 Url')
    corpapp = fields.Boolean(string=u"内部应用", default=True)
    home_url = fields.Char(string=u"应用主页地址")
    redirect_domain = fields.Char(string=u"可信域名")
    state = fields.Selection(
        string=u"状态",
        selection=[
            ('0', '停用'),
            ('1', '启用'),
            ('3', '未知'),
        ], default='1', required=True
    )

    @api.constrains('qr_login_id')
    def _check_one_login_id_only_bind_to_one_agent(self):
        """ 不允许同一个二维码登录设置被绑定到多个应用 """
        if self.qr_login_id:
            qr_login_count = self.search_count(
                [('work_id', '=', self.work_id.id), ('qr_login_id', '=', self.qr_login_id.id)])
            if qr_login_count > 1:
                raise ValidationError(_("同一个扫码登录设置被关联到了两个应用！"))

            #self.flush_recordset(['work_agent_ids', 'enabled'])
            # self.env.cr.execute(
            #     """SELECT work_id 
            #         FROM wechat_work_agent_config wwac 
            #         LEFT JOIN qr_login_provider qlp ON qlp.id=wwac.qr_login_id 
            #         WHERE qlp.enabled = true AND work_id IN 
            #         (SELECT work_id FROM wechat_work_agent_config WHERE id IN %s)
            #     GROUP BY work_id
            #     HAVING COUNT(*) > 1
            #     """,
            #     (tuple(self.ids),)
            # )
            # if self.env.cr.rowcount:
            #     raise ValidationError(
            #         _("一个企业微信号，只能有一个激活的二维码登录设置！"))

    @api.depends('icon_avatar_url')
    def _compute_icon_url(self):
        for res in self:
            if res.icon_avatar_url:
                res.icon_url = """<img src="{avatar_url}" width="60px" height="60px">""".format(
                    avatar_url=res.icon_avatar_url)
            else:
                res.icon_url = False

    @api.depends('work_id.company_id', 'agent_id')
    def _compute_message_handler_url(self):
        for agent in self:
            owner_website = self.env['website'].sudo(
            ).search([('company_id', '=', agent.work_id.company_id.id)], limit=1)
            if owner_website.exists():
                agent.message_handler_url = '%s/wechat/%s/handle_work_message' % (
                    owner_website.domain, agent.agent_id)
            else:
                agent.message_handler_url = 'No enabled'

    def _parse_values(self, values):
        if 'square_logo_url' in values:
            values['icon_avatar_url'] = values['square_logo_url']
        if 'agentid' in values:
            values['agent_id'] = values['agentid']
        if 'description' in values:
            values['remark'] = values['description']
        if 'close' in values:
            values['state'] = '1' if values['close'] == 0 else '0'

        _vals = {}
        for k, v in values.items():
            if k in self._fields:
                _vals[k] = v

        return _vals

    def wechat_work_sync(self, entry):
        update_count = 0
        for agent in self:
            if agent.corpapp:
                agent_record = self._parse_values(
                    entry.clients[agent.agent_id].agent.get(agent.agent_id))
                agent.write(agent_record)
            else:
                agent_record = self._parse_values(
                    entry.clients[agent.agent_id].agent.list()[0])
                agent.write(agent_record)

            update_count += 1
        return update_count
