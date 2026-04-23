# -*- coding: utf-8 -*-


from odoo import _, fields, models, api


class InclusiveFinancingRiskManageCreditsMixin(models.AbstractModel):
    _name = 'ifs.risk.manage.credits.mixin'
    _description = '个人征信详情'

    ifs_risk_credits_id = fields.Many2one(
        'ifs.risk.manage.credits', string='法人征信报告')
    strategy_id = fields.Char(
        string='贷前编号', related='ifs_risk_credits_id.strategy_id')
    conf_id = fields.Char(
        string='验证流程编号', related='ifs_risk_credits_id.conf_id')
    credit_name = fields.Char(
        string='姓名', related='ifs_risk_credits_id.name')
    credit_idcard = fields.Char(
        string='身份证号', related='ifs_risk_credits_id.idcard')
    credit_mobile = fields.Char(
        string='手机号', related='ifs_risk_credits_id.mobile')
    anti_fraud_rule_weight_ids = fields.One2many(
        related='ifs_risk_credits_id.anti_fraud_rule_weight_ids', string='反欺诈规则')
    verification_rule_weight_ids = fields.One2many(
        related='ifs_risk_credits_id.verification_rule_weight_ids', string='验证规则')
    anti_fraud_score_ids = fields.One2many(
        related='ifs_risk_credits_id.anti_fraud_score_ids', string='反欺诈评分')
    credit_score_ids = fields.One2many(
        related='ifs_risk_credits_id.credit_score_ids', string='信用评分')
    assessment_result_ids = fields.One2many(
        related='ifs_risk_credits_id.assessment_result_ids', string='评测结果')
    risk_statement_ids = fields.One2many(
        related='ifs_risk_credits_id.risk_statement_ids', string='风险提示')
    verification_ids = fields.One2many(
        related='ifs_risk_credits_id.verification_ids', string='验证规则')
    anti_fraud_rule_ids = fields.One2many(
        related='ifs_risk_credits_id.anti_fraud_rule_ids', string='反欺诈规则')
    bad_info_ids = fields.One2many(
        related='ifs_risk_credits_id.bad_info_ids', string='自然人识别')
    phone_address_ids = fields.One2many(
        related='ifs_risk_credits_id.phone_address_ids', string='手机号归属地')
    id_two_ids = fields.One2many(
        related='ifs_risk_credits_id.id_two_ids', string='身份证二要素验证')
    tel_check_ids = fields.One2many(
        related='ifs_risk_credits_id.tel_check_ids', string='手机三要素简版—移动联通电信')
    phone_verify_info_ids = fields.One2many(
        related='ifs_risk_credits_id.phone_verify_info_ids', string='手机信息验证')
    courtdetailpro_ids = fields.One2many(
        related='ifs_risk_credits_id.courtdetailpro_ids', string='法院信息详情——个人高级版')
    execution_ids = fields.One2many(
        related='ifs_risk_credits_id.execution_ids', string='法院被执行人——个人版')
    executionpro_ids = fields.One2many(
        related='ifs_risk_credits_id.executionpro_ids', string='法院被执行人——高级版')
    executionjud_ids = fields.One2many(
        related='ifs_risk_credits_id.executionjud_ids', string='法院裁判文书')
    executionlimited_ids = fields.One2many(
        related='ifs_risk_credits_id.executionlimited_ids', string='法院被执行人——限高版')
    specialList_c_ids = fields.One2many(
        related='ifs_risk_credits_id.specialList_c_ids', string='特殊名单验证')
    applyloan_bankapply_ids = fields.One2many(
        related='ifs_risk_credits_id.applyloan_bankapply_ids', string='借贷意向验证——本人在本机构借贷意向表现')
    applyloan_custcomertype_ids = fields.One2many(
        related='ifs_risk_credits_id.applyloan_custcomertype_ids', string='借贷意向验证——本人在各个客户类型借贷意向表现')
    applyloan_businesstype_ids = fields.One2many(
        related='ifs_risk_credits_id.applyloan_businesstype_ids', string='借贷意向验证——本人在各个业务类型借贷意向表现')
    applyloan_abnormaltime_ids = fields.One2many(
        related='ifs_risk_credits_id.applyloan_abnormaltime_ids', string='借贷意向验证——本人在异常时间段借贷意向表现')
    # 借贷风险勘测已通，但征信结果展示暂不需要该项数据，留作备用
    # applyloanusury_ids = fields.One2many(
    #     related='ifs_risk_credits_id.applyloanusury_ids', string='借贷风险勘测')
    totalloan_recent_ids = fields.One2many(
        related='ifs_risk_credits_id.totalloan_recent_ids', string='借贷行为验证——近期非银机构借贷情况')
    totalloan_history_ids = fields.One2many(
        related='ifs_risk_credits_id.totalloan_history_ids', string='借贷行为验证——历史非银机构借贷情况')
    # 申请信息评估已通，但征信结果展示暂不需要该项数据，留作备用
    # inforelation_idcard_ids = fields.One2many(
    #     related='ifs_risk_credits_id.inforelation_idcard_ids', string='申请信息评估——身份证号查询衍生变量')
    # inforelation_phone_ids = fields.One2many(
    #     related='ifs_risk_credits_id.inforelation_phone_ids', string='申请信息评估-手机号查询衍生变量')
    # inforelation_other_ids = fields.One2many(
    #     related='ifs_risk_credits_id.inforelation_other_ids', string='申请信息评估-其他查询衍生变量')
    fraudrelation_g_ids = fields.One2many(
        related='ifs_risk_credits_id.fraudrelation_g_ids', string='团伙欺诈排查-通用版')
    debtrepaystress_ids = fields.One2many(
        related='ifs_risk_credits_id.debtrepaystress_ids', string='偿债压力指数')
    # 朴道征信
    xycredit_ids = fields.One2many(
        related='ifs_risk_credits_id.xycredit_ids', string='轩辕分(标准版)')
    high_price_ids = fields.One2many(
        related='ifs_risk_credits_id.high_price_ids', string='高风险信用评分(标准版)')
    fraud_microscore_ids = fields.One2many(
        related='ifs_risk_credits_id.fraud_microscore_ids', string='⼩微企业主风险评分(标准版)')
    credit_enterprise_ids = fields.One2many(
        related='ifs_risk_credits_id.credit_enterprise_ids', string='小微企业综合信用评分(标准版)')
    credit_devmicroscore_ids = fields.One2many(
        related='ifs_risk_credits_id.credit_devmicroscore_ids', string='设备信用评分小微版(标准版)')
    highrisk_equ_ids = fields.One2many(
        related='ifs_risk_credits_id.highrisk_equ_ids', string='高危设备风险标签(标准版)')
    rela_nw_ids = fields.One2many(
        related='ifs_risk_credits_id.rela_nw_ids', string='斑马扩散(标准版)')
    credit_image_ids = fields.One2many(
        related='ifs_risk_credits_id.credit_image_ids', string='画像指标(标准版)——借贷行为画像')
    history_image_ids = fields.One2many(
        related='ifs_risk_credits_id.history_image_ids', string='画像指标(标准版)——历史消费汇总')
    ind_image_ids = fields.One2many(
        related='ifs_risk_credits_id.ind_image_ids', string='画像指标(标准版)——负债画像')
    level_image_ids = fields.One2many(
        related='ifs_risk_credits_id.level_image_ids', string='画像指标(标准版)——负债等级')
    capital_image_ids = fields.One2many(
        related='ifs_risk_credits_id.capital_image_ids', string='画像指标(标准版)——资产画像')
    grade_ability_ids = fields.One2many(
        related='ifs_risk_credits_id.grade_ability_ids', string='还款能力等级(标准版)')
    income_level_ids = fields.One2many(
        related='ifs_risk_credits_id.income_level_ids', string='偿债能力等级(标准版)')
    port_wealth_ids = fields.One2many(
        related='ifs_risk_credits_id.port_wealth_ids', string='财富画像(标准版)')
    risk_fraud_ids = fields.One2many(
        related='ifs_risk_credits_id.risk_fraud_ids', string='风险反欺诈评分(标准版)')

    guarantor_ifs_risk_credits_id = fields.Many2one(
        'ifs.risk.manage.credits', string='担保人征信报告')
    guarantor_credit_name = fields.Char(
        '姓名', related='guarantor_ifs_risk_credits_id.name')
    guarantor_credit_idcard = fields.Char(
        '身份证号', related='guarantor_ifs_risk_credits_id.idcard')
    guarantor_credit_mobile = fields.Char(
        '手机号', related='guarantor_ifs_risk_credits_id.mobile')
    guarantor_anti_fraud_rule_weight_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.anti_fraud_rule_weight_ids', string='反欺诈规则')
    guarantor_verification_rule_weight_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.verification_rule_weight_ids', string='验证规则')
    guarantor_anti_fraud_score_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.anti_fraud_score_ids', string='反欺诈评分')
    guarantor_credit_score_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.credit_score_ids', string='信用评分')
    guarantor_assessment_result_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.assessment_result_ids', string='评测结果')
    guarantor_risk_statement_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.risk_statement_ids', string='风险提示')
    guarantor_verification_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.verification_ids', string='验证规则')
    guarantor_anti_fraud_rule_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.anti_fraud_rule_ids', string='反欺诈规则')
    guarantor_bad_info_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.bad_info_ids', string='自然人识别')
    guarantor_phone_address_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.bad_info_ids', string='手机号归属地')
    guarantor_id_two_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.phone_address_ids', string='身份证二要素验证')
    guarantor_tel_check_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.tel_check_ids', string='手机三要素简版—移动联通电信')
    guarantor_phone_verify_info_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.phone_verify_info_ids', string='手机信息验证')
    guarantor_courtdetailpro_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.courtdetailpro_ids', string='法院信息详情——个人高级版')
    guarantor_execution_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.execution_ids', string='法院被执行人——个人版')
    guarantor_executionpro_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.executionpro_ids', string='法院被执行人——高级版')
    guarantor_executionjud_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.executionjud_ids', string='法院裁判文书')
    guarantor_executionlimited_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.executionlimited_ids', string='法院被执行人——限高版')
    guarantor_specialList_c_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.specialList_c_ids', string='特殊名单验证')
    guarantor_applyloan_bankapply_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.applyloan_bankapply_ids', string='借贷意向验证——本人在本机构借贷意向表现')
    guarantor_applyloan_custcomertype_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.applyloan_custcomertype_ids', string='借贷意向验证——本人在各个客户类型借贷意向表现')
    guarantor_applyloan_businesstype_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.applyloan_businesstype_ids', string='借贷意向验证——本人在各个业务类型借贷意向表现')
    guarantor_applyloan_abnormaltime_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.applyloan_abnormaltime_ids', string='借贷意向验证——本人在异常时间段借贷意向表现')
    # 借贷风险勘测已通，但征信结果展示暂不需要该项数据，留作备用
    # guarantor_applyloanusury_ids = fields.One2many(
    #     related='guarantor_ifs_risk_credits_id.applyloanusury_ids', string='借贷风险勘测')
    guarantor_totalloan_recent_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.totalloan_recent_ids', string='借贷行为验证——近期非银机构借贷情况')
    guarantor_totalloan_history_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.totalloan_history_ids', string='借贷行为验证——历史非银机构借贷情况')
    # 申请信息评估已通，但征信结果展示暂不需要该项数据，留作备用
    # guarantor_inforelation_idcard_ids = fields.One2many(
    #     related='guarantor_ifs_risk_credits_id.inforelation_idcard_ids', string='申请信息评估——身份证号查询衍生变量')
    # guarantor_inforelation_phone_ids = fields.One2many(
    #     related='guarantor_ifs_risk_credits_id.inforelation_phone_ids', string='申请信息评估-手机号查询衍生变量')
    # guarantor_inforelation_other_ids = fields.One2many(
    #     related='guarantor_ifs_risk_credits_id.inforelation_other_ids', string='申请信息评估-其他查询衍生变量')
    guarantor_fraudrelation_g_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.fraudrelation_g_ids', string='团伙欺诈排查-通用版')
    guarantor_debtrepaystress_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.debtrepaystress_ids', string='偿债压力指数')
    # 朴道征信
    guarantor_xycredit_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.xycredit_ids', string='轩辕分(标准版)')
    guarantor_high_price_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.high_price_ids', string='高风险信用评分(标准版)')
    guarantor_fraud_microscore_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.fraud_microscore_ids', string='⼩微企业主风险评分(标准版)')
    guarantor_credit_enterprise_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.credit_enterprise_ids', string='小微企业综合信用评分(标准版)')
    guarantor_credit_devmicroscore_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.credit_devmicroscore_ids', string='设备信用评分小微版(标准版)')
    guarantor_highrisk_equ_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.highrisk_equ_ids', string='高危设备风险标签(标准版)')
    guarantor_rela_nw_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.rela_nw_ids', string='斑马扩散(标准版)')
    guarantor_credit_image_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.credit_image_ids', string='画像指标(标准版)——借贷行为画像')
    guarantor_history_image_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.history_image_ids', string='画像指标(标准版)——历史消费汇总')
    guarantor_ind_image_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.ind_image_ids', string='画像指标(标准版)——负债画像')
    guarantor_level_image_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.level_image_ids', string='画像指标(标准版)——负债等级')
    guarantor_capital_image_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.capital_image_ids', string='画像指标(标准版)——资产画像')
    guarantor_grade_ability_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.grade_ability_ids', string='还款能力等级(标准版)')
    guarantor_income_level_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.income_level_ids', string='偿债能力等级(标准版)')
    guarantor_port_wealth_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.port_wealth_ids', string='财富画像(标准版)')
    guarantor_risk_fraud_ids = fields.One2many(
        related='guarantor_ifs_risk_credits_id.risk_fraud_ids', string='风险反欺诈评分(标准版)')
