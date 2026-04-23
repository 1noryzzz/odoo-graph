# -*- coding: utf-8 -*-
import asyncio
import logging

from odoo import _, fields, models, api
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class InclusiveFinancingRiskManageCredits(models.Model):
    _name = 'ifs.risk.manage.credits'
    _description = '个人征信信息'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"
    _rec_name = 'name'

    ifs_company_id = fields.Many2one(
        'ifs.base.company', required=True, ondelete='restrict', index=True, string='金融业务参与方')
    name = fields.Char(string='姓名', required=True, tracking=True)
    idcard = fields.Char(
        string='身份证号', required=True, index=True)
    mobile = fields.Char(
        string='手机号', required=True, tracking=True)
    strategy_id = fields.Char(string='贷前编号', default='STR0038612')
    conf_id = fields.Char(string='验证流程编号', default='MCP0038613')
    is_fetch_credit = fields.Boolean('是否已经抓取征信信息', default=False)
    is_fetch_pd_credit = fields.Boolean('是否已经抓取朴道征信信息', default=False)

    credits_details_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', 'risk_credits_id', string='征信信息详情')
    anti_fraud_rule_weight_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='反欺诈规则')
    verification_rule_weight_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='验证规则')
    anti_fraud_score_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='反欺诈评分')
    credit_score_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='信用评分')
    assessment_result_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='评测结果')
    # 风险提示
    risk_statement_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='风险提示')
    verification_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='验证规则')
    anti_fraud_rule_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='反欺诈规则')
    bad_info_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='自然人识别')
    phone_address_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='手机号归属地')
    id_two_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='身份证二要素验证')
    tel_check_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='手机三要素简版—移动联通电信')
    phone_verify_info_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='手机信息验证')
    courtdetailpro_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='法院信息详情——个人高级版')
    execution_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='法院被执行人——个人版')
    executionpro_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='法院被执行人——高级版')
    executionjud_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='法院裁判文书')
    executionlimited_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='法院被执行人——限高版')
    specialList_c_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='特殊名单验证')
    applyloan_bankapply_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在本机构借贷意向表现')
    applyloan_custcomertype_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在各个客户类型借贷意向表现')
    applyloan_businesstype_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在各个业务类型借贷意向表现')
    applyloan_abnormaltime_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在异常时间段借贷意向表现')
    # 借贷风险勘测已通，但征信结果展示暂不需要该项数据，留作备用
    # applyloanusury_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷风险勘测')
    totalloan_recent_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷行为验证——近期非银机构借贷情况')
    totalloan_history_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷行为验证——历史非银机构借贷情况')
    # 申请信息评估已通，但征信结果展示暂不需要该项数据，留作备用
    # inforelation_idcard_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='申请信息评估——身份证号查询衍生变量')
    # inforelation_phone_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='申请信息评估-手机号查询衍生变量')
    # inforelation_other_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='申请信息评估-其他查询衍生变量')
    fraudrelation_g_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='团伙欺诈排查-通用版')
    debtrepaystress_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='偿债压力指数')
    
    #朴道征信
    xycredit_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='轩辕分(标准版)')
    high_price_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='高风险信用评分(标准版)')
    fraud_microscore_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='⼩微企业主风险评分(标准版)')
    credit_enterprise_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='小微企业综合信用评分(标准版)')
    credit_devmicroscore_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='设备信用评分小微版(标准版)')
    # 特殊名单_升级版(标准版)此接口暂时不需要,百融接口已查得该项数据，留作备用，不过未开通
    # special_plus_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='特殊名单_升级版(标准版)')
    # 借贷申请行为(标准版)此接口暂时不需要,百融接口已查得该项数据，留作备用，已开通
    # apply_self_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在本机构借贷意向表现')
    # apply_custcomer_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在各个客户类型借贷意向表现')
    # apply_abnormal_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷意向验证——本人在异常时间段借贷意向表现')
    highrisk_equ_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='高危设备风险标签(标准版)')
    rela_nw_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='斑马扩散(标准版)')
    credit_image_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='画像指标(标准版)——借贷行为画像')
    history_image_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='画像指标(标准版)——历史消费汇总')
    ind_image_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='画像指标(标准版)——负债画像')
    level_image_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='画像指标(标准版)——负债等级')
    capital_image_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='画像指标(标准版)——资产画像')
    grade_ability_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='还款能力等级(标准版)')
    income_level_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='偿债能力等级(标准版)')
    port_wealth_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='财富画像(标准版)')
    risk_fraud_ids = fields.One2many(
        'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='风险反欺诈评分(标准版)')
    
    # port_applyday_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='当日借贷申请行为(标准版)')
    # # debtrepaystress_ids = fields.One2many(
    # #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='反欺诈风险评分(标准版)')
    # cheat_applyantifraud_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='反欺诈评分(标准版)')
    # veri_cell_interrelated_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='高危涉网数据手机号核验(标准版)')
    # network_level_std_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='关系网络等级(标准版)')
    # loan_assess_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='借贷评估标签(标准版)')
    # lable_com_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='客群标签(综合类)')
    # fraud_score_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='欺诈分(标准版)')
    # # 不良行为评估(标准版)此接口暂时不需要，留作备用
    # # riskbehavior_assess_ids = fields.One2many(
    # #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='不良行为评估(标准版)')
    # htcredit_general_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='设备风险信用评分(通用客群)')
    # credit_py_basic_ids = fields.One2many(
    #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='信用风险评分基础版(标准版)')
    # # 共债分(标准版)此接口暂时不需要，留作备用
    # # total_debit_ids = fields.One2many(
    # #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='共债分(标准版)')
    # # debtrepaystress_ids = fields.One2many(
    # #     'ifs.risk.manage.credits.detail', compute='_compute_credits_details_ids', string='综合风险标签(标准版)')

    @api.depends('ifs_company_id')
    def _compute_credits_details_ids(self):
        detail_ids = {
            'anti_fraud_rule_weight_ids': 'RULE-WEIGHT',
            'verification_rule_weight_ids': 'FINAL-WEIGHT',
            'anti_fraud_score_ids': 'SCOREAF',
            'credit_score_ids': 'SCORE',
            'assessment_result_ids': 'FINAL-DECISION',
            'verification_ids': 'INFO-VERIFICATION',
            'anti_fraud_rule_ids': 'RULE-INFO',
            'bad_info_ids': 'PERSON-CHECK',
            'phone_address_ids': 'PHONE-ADDRESS',
            'id_two_ids': 'ID-TWO',
            'tel_check_ids': 'TEL-CHECK',
            'phone_verify_info_ids': 'TEL-INFO',
            'courtdetailpro_ids': 'COURT-DETAILPRO',
            'execution_ids': 'EXECUTION',
            'executionpro_ids': 'EXECUTIONPRO',
            'executionjud_ids': 'EXECUTIONJUD',
            'executionlimited_ids': 'EXECUTIONLIMITED',
            'specialList_c_ids': 'SPECIALLIST-C',
            'applyloan_bankapply_ids': 'APPLYLOAN-BANKAPPLY',
            'applyloan_custcomertype_ids': 'APPLYLOAN-CUSTCOMER',
            'applyloan_businesstype_ids': 'APPLYLOAN-BUSINESSTYPE',
            'applyloan_abnormaltime_ids': 'APPLYLOAN-ABNORMAITIME',
            # 'applyloanusury_ids': 'APPLYLOANUSURY',
            'totalloan_recent_ids': 'TOTALLOAN-RECENT',
            'totalloan_history_ids': 'TOTALLOAN-HISTORY',
            # 'inforelation_idcard_ids': 'INFORELATION-IDCARD',
            # 'inforelation_phone_ids': 'INFORELATION-PHONE',
            # 'inforelation_other_ids': 'INFORELATION-OTHER',
            'fraudrelation_g_ids': 'FRAUDRELATION-G',
            'debtrepaystress_ids': 'DEBTREPAYSTRESS',
            'risk_statement_ids': '',
            #朴道征信
            'xycredit_ids': 'HQXYF',
            'high_price_ids': 'HQGFXXYPF',
            'fraud_microscore_ids': 'HQXWQYZFXPF',
            'credit_enterprise_ids': 'HQXWQYZHXYPF',
            'credit_devmicroscore_ids': 'HQSBXYPFXWB',
            # 'special_plus_ids': 'SPECIALLIST-PLUS',
            # 'apply_self_ids': 'PORT-APPLY',
            # 'apply_custcomer_ids': 'PORT-CUSTCOMER',
            # 'apply_abnormal_ids': 'PORT-ABNORMAL',
            'highrisk_equ_ids': 'HQGWSBFXBQ',
            'rela_nw_ids': 'HQBMKS',
            'credit_image_ids': 'RISK-CREDIT',
            'history_image_ids': 'RISK-HIS',
            'ind_image_ids': 'RISK-IND',
            'level_image_ids': 'RISK-LEVEL',
            'capital_image_ids': 'RISK-CAPITAL',
            'grade_ability_ids': 'HQHKNLDJ',
            'income_level_ids': 'HQCZNLDJ',
            'port_wealth_ids': 'HQCFHX',
            'risk_fraud_ids': 'HQFXFQZPF',
            
            # 'port_applyday_ids': 'HQDRJDSQXW',
            # # 'debtrepaystress_ids': '',
            # 'cheat_applyantifraud_ids': 'HQFQZPF-PDZX',
            # 'veri_cell_interrelated_ids': 'HQGWSWSJSJHHY',
            # 'network_level_std_ids': 'HQGXWLDJ',
            # 'loan_assess_ids': 'HQJDPGBQ',
            # 'lable_com_ids': 'HQKQBQ',
            # 'fraud_score_ids': 'HQQZFXX',
            # # 'riskbehavior_assess_ids': '',
            # 'htcredit_general_ids': 'HQSBFXXYPF',
            # 'credit_py_basic_ids': 'HQXYFXPFJCB',
            # # 'total_debit_ids': '',
            # # 'debtrepaystress_ids': '',
        }
        for key, value in detail_ids.items():
            self._detail_ids(key, value)

    def _detail_ids(self, field, code):
        for record in self:
            record[field] = False # :TODO []  待验证
            if record.credits_details_ids:
                record[field] = record.credits_details_ids.filtered(
                    lambda r: r.code == code)
                if field == 'risk_statement_ids':
                    record[field] = record['verification_ids'] + \
                        record['anti_fraud_rule_ids']

    def start_risk_fetch(self, api_codes):
        asyncio.run(self._fetch_credit_all(api_codes))

    async def _fetch_credit_all(self, api_codes):
        Config = self.env['ir.config_parameter'].sudo()
        sync_frequency = Config.get_param(
            'ifs_base.risk_manage_credits_update_frequency', 'quarterly')

        # will_fetch_ifs_credits = self.search(
        #     ['|', ('is_fetch_credit', '=', False), '&', ('is_fetch_credit', '=', True), ('ifs_company_id.last_fetch_credit_time', '<', self._next_fetch_date(sync_frequency))])
        will_fetch_ifs_credits = self.search([('is_fetch_credit', '=', False)])
        tasks = []
        for ifs_credit in will_fetch_ifs_credits:
            try:
                task = asyncio.create_task(ifs_credit._fetch_credit_info(api_codes))
                tasks.append(task)
            except Exception as e:
                _logger.error(repr(e))
                continue
        await asyncio.gather(*tasks)

    async def _fetch_credit_info(self, api_codes):
        for api_code in api_codes:
            if api_code == 'BR-QYZXCX-STR':
                req = self.env['galaxy.external.api'].invoke(api_code, body={
                    'strategy_id': 'STR0038612',
                    'idcard': self.idcard,
                    'mobile': self.mobile,
                    'name': self.name,
                })
            if api_code == 'BR-QYZXCX-MCP':
                req = self.env['galaxy.external.api'].invoke(api_code, body={
                    'conf_id': 'MCP0038613',
                    'idcard': self.idcard,
                    'mobile': self.mobile,
                    'name': self.name,
                })
            update_detail_ids = {
                'credits_details_ids': [fields.Command.create({
                    'code': rdata.code,
                    'definition_id': rdata.definition_id.id,
                    'raw': rdata.raw,
                }) for rdata in req.response_ids],
            }
            self.write(update_detail_ids)
            # if self.is_fetch_credit:
            #     update_detail_ids.update({
            #         'ifs_company_id': self.ifs_company_id.id,
            #         'idcard': self.idcard,
            #         'mobile': self.mobile,
            #         'name': self.name,
            #         'is_fetch_credit': True
            #     })
            #     if self.name == self.ifs_company_id.legal_id.name:
            #         self.ifs_company_id.last_risk_credit_id = self.create(update_detail_ids).id
            #     elif self.name == self.ifs_company_id.principal_id.name:
            #         self.ifs_company_id.last_guarantor_risk_credit_id = self.create(update_detail_ids).id
            # else:
            #     self.write(update_detail_ids)
        self.is_fetch_credit = True
        self.ifs_company_id.update({
            'last_fetch_credit_time': fields.Datetime.now()
        })
        
    def start_risk_fetch_pd(self, api_codes):
        asyncio.run(self._fetch_pd_credit_all(api_codes))
        
    async def _fetch_pd_credit_all(self, api_codes):
        Config = self.env['ir.config_parameter'].sudo()
        sync_frequency = Config.get_param(
            'ifs_base.risk_manage_credits_update_frequency', 'quarterly')

        # will_fetch_ifs_credits = self.search(
        #     ['|', ('is_fetch_pd_credit', '=', False), '&', ('is_fetch_pd_credit', '=', True), ('ifs_company_id.last_fetch_pd_credit_time', '<', self._next_fetch_date(sync_frequency))])
        will_fetch_ifs_credits = self.search([('is_fetch_pd_credit', '=', False)])
        tasks = []
        for ifs_credit in will_fetch_ifs_credits:
            try:
                task = asyncio.create_task(ifs_credit._fetch_pd_credit_info(api_codes))
                tasks.append(task)
            except Exception as e:
                _logger.error(repr(e))
                continue
        await asyncio.gather(*tasks)
        
    async def _fetch_pd_credit_info(self, api_codes):
        code_list = {
            'PDZX-SCORE-XYCREDIT': 'score_xycredit_st', 
            'PDZX-GFXXYPF-BZB': 'score_high_price_st', 
            'PDZX-SCORE-FRAUD-MICROSCORE-EST': 'score_fraud_microscore_est', 
            'PDZX-XWQYZHXYPF-BZB': 'score_credit_enterprise_st', 
            'PDZX-SBXYPFXWB-BZB': 'score_credit_devmicroscore_st', 
            # 'PDZX-SPECIAL-PLUS': 'port_special_plus_st', 
            # 'PDZX-JDSQXW-BZB': 'port_apply_st', 
            'PDZX-GWSBFXBQ-BZB': 'port_highrisk_equ_st', 
            'PDZX-RALA-NW': 'port_rela_nw_st',  
            'PDZX-RISK-IND': 'port_risk_ind_st', 
            'PDZX-HKNLDJ-BZB': 'port_grade_ability_st', 
            'PDZX-CZNLDJ-BZB': 'port_income_level_st', 
            'PDZX-WEALTH': 'port_wealth_st', 
            'PDZX-FXFQZPF-BZB': 'score_risk_fraud_st', 
            
            # 'PDZX-DRJDSQXW-BZB': 'port_applyday_st', 
            # 'PDZX-GXWLDJ-BZB': 'port_network_level_std_st', 
            # 'PDZX-LABEL-COM': 'port_lable_com_st', 
            # 'PDZX-QZF-BZB': 'score_fraud_score_st',
            # 'PDZX-SCORE-PY-BASIC': 'score_credit_py_basic_st', 
            # 'PDZX-TOTAL-DEBIT': 'port_total_debit_st', 
            # 'PDZX-JDPGBQ-BZB': 'port_loan_assess_st', 
            # # 'PDZX-ZHFXBQ-BZB': '', 
            # # 'PDZX-FQZFXPF-BZB': '', 
            # 'PDZX-GWSWSJSJHHY-BZB': 'veri_cell_interrelated_st', 
            # 'PDZX-RISKBRHAVIOR-ASSESS': 'port_riskbehavior_assess_st', 
            # 'PDZX-SBFXXYPF-TYKQ': 'score_htcredit_general_st', 
            # 'PDZX-FQZPF-BZB': 'score_cheat_applyantifraud_st',
        }
        for api_code in api_codes:
            for key,item in code_list.items():
                if key == api_code:
                    body = {
                        'prod_cd': item,
                        'qry_rsn': '0',
                        'occ_orgn': '91350128MA327RP99H',
                        'cert_no': self.idcard,
                        'cert_type': '0',
                        'cert_name': self.name,
                        'mobile': self.mobile,
                    }
            #反欺诈评分(标准版)
            if api_code == 'PDZX-FQZPF-BZB':
                body.update({
                    'scene': '',
                    'service': '',
                })
            #风险反欺诈评分(标准版)
            if api_code == 'PDZX-FXFQZPF-BZB':
                body.update({
                    'imei': '',
                })
            #借贷评估标签(标准版)
            if api_code == 'PDZX-JDPGBQ-BZB':
                body.pop('mobile')
                body.update({
                    'api_key': '84d6bb0a4df14917a035830334d0d18b',
                    'api_secret': '',
                })
            #设备风险信用评分(通用客群)
            #小微企业综合信用评分(标准版)
            if api_code == 'PDZX-SBFXXYPF-TYKQ' or api_code == 'PDZX-XWQYZHXYPF-BZB':
                body.pop('cert_no')
                body.pop('cert_type')
                body.pop('cert_name')
                body.update({
                    'req_data': '', # 产品请求参数，可空，具体作用未知
                    'imei': '', # 安卓设备识别码，若手机号有值，先传手机号
                    'idfa': '', # 苹果广告标识符，若安卓设备识别码有值，先传安卓设备识别码
                })
            #设备信用评分小微版(标准版)
            if api_code == 'PDZX-SBXYPFXWB-BZB':
                body.update({
                    'id_type': 'phone', # 入参类型，idfa/imei/phone，若填phone，则另外两个值可不填
                    'imei': '', # 设备识别码，id_type不为imei时可为空
                    'idfa': '', # 苹果广告标识符，id_type不为idfa时可为空
                })
            #⼩微企业主风险评分(标准版)
            if api_code == 'PDZX-SCORE-FRAUD-MICROSCORE-EST':
                body.update({
                    'company_no': '', # 企业身份标识码，如果有手机号，可不填，如果填了，则先传这个
                    'company_name': '', # 企业名称，可不填
                    'company_no_type': '1', # 企业身份标识码类型，必填，无取值说明
                })
            #共债分(标准版)此接口暂时不需要，留作备用
            if api_code == 'PDZX-TOTAL-DEBIT':
                body.update({
                    'cut_type': '1', # 查询类型,枚举值：1：贷款审批；2：信用卡审批；3：贷后管理,输入其他值会报错
                })
            #财富画像(标准版)
            if api_code == 'PDZX-WEALTH':
                body.update({
                    'imei': '', # 设备识别码，可为空
                })
            #综合风险标签(标准版)
            #反欺诈风险评分(标准版)
            req = self.env['galaxy.external.api'].invoke(api_code, body=body)
            update_detail_ids = {
                'credits_details_ids': [fields.Command.create({
                    'code': rdata.code,
                    'definition_id': rdata.definition_id.id,
                    'raw': rdata.raw,
                }) for rdata in req.response_ids],
            }
            self.write(update_detail_ids)
        self.is_fetch_pd_credit = True
        self.ifs_company_id.update({
            'last_fetch_pd_credit_time': fields.Datetime.now()
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


class InclusiveFinancingRiskManageCredits(models.Model):
    _name = 'ifs.risk.manage.credits.detail'
    _description = '个人征信信息详情'
    _inherit = ['galaxy.external.api.response.data.mixin']
    _order = 'write_date desc'

    risk_credits_id = fields.Many2one(
        'ifs.risk.manage.credits', required=True, ondelete='restrict', delegate=True, index=True,
        string='个人征信', help='此参与者作为公司主要人员，需要的征信资料信息')
    code = fields.Char('结果标识')
