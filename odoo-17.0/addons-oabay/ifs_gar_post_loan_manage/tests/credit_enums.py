from enum import Enum


"""HY-征信接口常用枚举常量"""


class CodeEnumMixin:
    """
    通用 code 枚举能力
    """

    @classmethod
    def from_code(cls, code: str):
        try:
            return cls(code)
        except ValueError:
            raise ValueError(f"{cls.__name__} invalid code: {code}")

    @classmethod
    def has_code(cls, code: str) -> bool:
        return code in cls._value2member_map_

    @classmethod
    def list_codes(cls):
        return [e.value for e in cls]


class IdType(CodeEnumMixin, str, Enum):
    """
    证件类型（按你确认的“调整后”取值）。
    """

    EMPLOYEE_CODE = "00"  # 员工代码
    RESIDENT_ID = "20"  # 身份证
    PASSPORT = "22"  # 护照
    HK_MACAO_PASS = "25"  # 港澳居民来往内地通行证
    TAIWAN_PASS = "26"  # 台湾居民来往大陆通行证
    OTHER = "2X"  # 其他证件
    ORG_CODE_CERT = "30"  # 组织机构代码证


class Sex(CodeEnumMixin, str, Enum):
    """
    申请人性别。
    """

    MALE = "1"  # 男
    FEMALE = "2"  # 女
    UNKNOWN = "3"  # 未知


class MaritalStatus(CodeEnumMixin, str, Enum):
    """
    婚姻状况。
    """

    UNMARRIED = "10"  # 未婚
    MARRIED = "20"  # 已婚
    DIVORCED = "40"  # 离异
    WIDOWED = "50"  # 丧偶
    FIRST_MARRIAGE = "21"  # 初婚
    REMARRIAGE = "01"  # 复婚
    RE_MARRIAGE_ALT = "0"  # 再婚
    UNKNOWN = "90"  # 未知


class Education(CodeEnumMixin, str, Enum):
    """
    最高学历。
    """

    MASTER_OR_ABOVE = "0"  # 硕士及以上
    BACHELOR = "10"  # 本科
    JUNIOR_COLLEGE = "20"  # 大专
    HIGH_SCHOOL = "30"  # 高中
    MIDDLE_OR_BELOW = "40"  # 初中及以下
    OTHER = "50"  # 其他
    TECHNICAL_SECONDARY = "60"  # 中专
    VOCATIONAL_HIGH = "70"  # 职高


class Degree(CodeEnumMixin, str, Enum):
    """
    最高学位。
    """

    NONE = "0"  # 无学位
    HONORARY_DOCTOR = "100"  # 名誉博士
    DOCTOR = "200"  # 博士
    MASTER = "300"  # 硕士
    BACHELOR = "400"  # 学士
    UNKNOWN = "999"  # 未知


class LiveInfo(CodeEnumMixin, str, Enum):
    """
    现住房情况（住房性质）。
    """

    OWN_NO_LOAN = "10"  # 自购现无贷款
    OWN_WITH_LOAN = "20"  # 自购现有贷款
    LIVE_WITH_PARENTS = "30"  # 与父母同住
    HOMESTEAD = "40"  # 宅基地房
    RENT = "50"  # 租房
    PUBLIC_HOUSING = "60"  # 公有住宅
    DORMITORY = "70"  # 集体宿舍
    OTHER = "99"  # 其他


class EmploymentStatus(CodeEnumMixin, str, Enum):
    """
    就业状况。
    """

    EMPLOYED = "91"  # 在职
    UNKNOWN = "99"  # 未知


class CompanyType(CodeEnumMixin, str, Enum):
    """
    单位性质（indivType）。
    """

    GOVERNMENT = "A"  # 政府机构
    STATE_OWNED = "B"  # 国企
    FOREIGN_OR_JOINT = "C"  # 外资/合资
    PRIVATE = "D"  # 民营
    SELF_EMPLOYED = "E"  # 个体
    FINANCIAL = "R"  # 金融机构
    PUBLIC_INSTITUTION = "S"  # 事业单位
    OTHER = "Z"  # 其他


class Position(CodeEnumMixin, str, Enum):
    """
    职业（position）。
    """

    LEADER = "0"  # 国家机关、党群组织、企业、事业单位负责人
    PROFESSIONAL = "1"  # 专业技术人员
    OFFICE_STAFF = "3"  # 办事人员和有关人员
    SERVICE_STAFF = "4"  # 商业、服务业人员
    PRIMARY_INDUSTRY = "5"  # 农、林、牧、渔、水利业生产人员
    OPERATOR = "6"  # 生产、运输设备操作人员及有关人员
    SOLDIER = "X"  # 军人
    OTHER = "Y"  # 不便分类的其他从业人员
    UNKNOWN = "Z"  # 未知


class IndustryType(CodeEnumMixin, str, Enum):
    """
    贷款用户所属行业类别（induInvol）。
    """

    AGRICULTURE = "1"  # 农、林、牧、渔业
    MINING = "2"  # 采矿业
    MANUFACTURING = "3"  # 制造业
    UTILITIES = "4"  # 电力、热力、燃气及水生产和供应业
    CONSTRUCTION = "5"  # 建筑业
    WHOLESALE_RETAIL = "6"  # 批发和零售业
    TRANSPORT_LOGISTICS_POSTAL = "7"  # 交通运输、仓储和邮政业
    HOTEL_CATERING = "8"  # 住宿和餐饮业
    IT_SOFTWARE = "9"  # 信息传输、软件和信息技术服务业
    FINANCE = "10"  # 金融业
    REAL_ESTATE = "11"  # 房地产业
    LEASING_BUSINESS_SERVICES = "12"  # 租赁和商务服务业
    SCI_RESEARCH_TECH = "13"  # 科学研究和技术服务业
    WATER_ENV_PUBLIC_FACILITIES = "14"  # 水利、环境和公共设施管理业
    RESIDENT_SERVICES = "15"  # 居民服务、修理和其他服务业
    EDUCATION = "16"  # 教育
    HEALTH_SOCIAL_WORK = "17"  # 卫生和社会工作
    CULTURE_SPORT_ENTERTAINMENT = "18"  # 文化、体育和娱乐业
    PUBLIC_ADMIN_SOCIAL_ORG = "19"  # 公共管理、社会保障和社会组织
    INTERNATIONAL_ORG = "20"  # 国际组织
    OTHER = "21"  # 其他


class Duty(CodeEnumMixin, str, Enum):
    """
    职务（duty）。
    """

    SENIOR_LEADER = "1"  # 高级领导
    MIDDLE_LEADER = "2"  # 中级领导
    STAFF = "3"  # 一般员工
    OTHER = "4"  # 其他


class Caste(CodeEnumMixin, str, Enum):
    """
    职称（caste）。
    """

    NONE = "01"  # 无职称
    SENIOR = "02"  # 高级
    MIDDLE = "03"  # 中级
    JUNIOR = "04"  # 初级
    OTHER = "05"  # 其他


class Country(CodeEnumMixin, str, Enum):
    """
    国籍代码（当前只显式定义文档要求值）。
    """

    CHINA = "156"  # 中华人民共和国


class GuaranteeAcctType(CodeEnumMixin, str, Enum):
    """
    担保账户类型（acctType）。
    """

    FINANCING_GUARANTEE = "G1"  # 融资担保账户
    NON_FINANCING_GUARANTEE = "G2"  # 非融资担保账户


class GuaranteeBusinessLine(CodeEnumMixin, str, Enum):
    """
    担保业务大类（busiLines）。
    """

    FINANCING_GUARANTEE = "1"  # 融资担保
    NON_FINANCING_GUARANTEE = "2"  # 非融资担保
    RE_GUARANTEE = "3"  # 再担保
    GUARANTEE_INSURANCE = "4"  # 保证保险


class GuaranteeBusinessDetailLine(CodeEnumMixin, str, Enum):
    """
    担保业务种类细分（busiDtlLines）。
    """

    # 融资担保
    LOAN_GUARANTEE = "01"  # 贷款担保
    BILL_ACCEPTANCE_GUARANTEE = "02"  # 票据承兑担保
    TRADE_FINANCE_GUARANTEE = "03"  # 贸易融资担保
    PROJECT_FINANCE_GUARANTEE = "04"  # 项目融资担保
    LETTER_OF_CREDIT_GUARANTEE = "05"  # 信用证担保
    OTHER_FINANCING_GUARANTEE = "06"  # 其他融资担保
    BOND_ISSUANCE_GUARANTEE = "10"  # 债券发行担保
    # 非融资担保
    LITIGATION_PRESERVATION_GUARANTEE = "07"  # 诉讼保全担保
    PERFORMANCE_GUARANTEE = "08"  # 履约担保
    OTHER_NON_FINANCING_GUARANTEE = "09"  # 其他非融资担保
    # 再担保
    RE_GUARANTEE = "11"  # 再担保
    # 保证保险
    LOAN_GUARANTEE_INSURANCE = "12"  # 贷款保证保险
    CONSUMER_CREDIT_GUARANTEE_INSURANCE = "13"  # 个人消费信用保证保险


class Currency(CodeEnumMixin, str, Enum):
    """
    币种（loanCcy）。
    """

    CNY = "CNY"  # 人民币


class GuaranteeMode(CodeEnumMixin, str, Enum):
    """
    反担保方式（guraMode）。
    """

    CREDIT = "0"  # 信用/免担保
    ASSURANCE = "1"  # 保证
    PLEDGE = "2"  # 质押
    MORTGAGE = "3"  # 抵押
    COMBINATION = "4"  # 组合


class OtherRepaymentGuaranteeWay(CodeEnumMixin, str, Enum):
    """
    其他还款保证方式（othRepyGuraWay）。
    """

    NONE = "0"  # 无
    DEPOSIT = "1"  # 保证金
    OTHER = "9"  # 其他


class RelatedRepayObligorInfoldType(CodeEnumMixin, str, Enum):
    '''
    相关还款责任人 身份类别
    '''

    NATURAL_PERSON = "1"  # 自然人
    ORGANIZATION = "2"  # 组织机构


class RelatedRepayObligorCertType(CodeEnumMixin, str, Enum):
    '''
    相关责任人身份标识类型
    '''

    HOUSEHOLD_REGISTER = "1"  # 户口簿
    PASSPORT = "2"  # 护照
    MAINLAND_TRAVEL_PERMIT_HK_MACAU = "5"  # 港澳居民来往内地通行证
    MAINLAND_TRAVEL_PERMIT_TAIWAN = "6"  # 台湾同胞来往内地通行证
    FOREIGNER_RESIDENCE_PERMIT = "8"  # 外国人居留证
    POLICE_ID = "9"  # 警官证
    HK_ID_CARD = "A"  # 香港身份证
    MACAU_ID_CARD = "B"  # 澳门身份证
    TAIWAN_ID_CARD = "C"  # 台湾身份证
    OTHER = "X"  # 其他证件
    ID_CARD_AND_SIMILAR = "10"  # 居民身份证及其他以公民身份证号码为标识的证件
    MILITARY_ID = "20"  # 军人身份证件


class OrganizationCertType(CodeEnumMixin, str, Enum):
    '''
    企业身份标识类型
    适用条件：
    - 当 相关还款责任人 身份类别 = 2(组织机构) 时使用
    '''

    ZHONGZHENG_CODE = "10"  # 中征码（原贷款卡编码）
    UNIFIED_SOCIAL_CREDIT_CODE = "20"  # 统一社会信用代码
    ORG_CODE = "30"  # 组织机构代码


class RepayObligorType(CodeEnumMixin, str, Enum):
    """
    还款责任人类型（arlpType）。
    """

    JOINT_DEBTOR = "1"  # 共同债务人
    COUNTER_GUARANTOR = "2"  # 反担保人
    OTHER = "9"  # 其他


class WartySign(CodeEnumMixin, str, Enum):
    """
    联保标志（wartySign）。
    """

    SINGLE_OR_SPLIT = "0"  # 单人保证/多人分保
    JOINT = "1"  # 联保


class LiabilityAcctStatus(CodeEnumMixin, str, Enum):
    """
    在保责任-账户状态（liabInfo.acctStatus）。
    """

    NORMAL = "1"  # 正常
    CLOSED = "2"  # 关闭


class FiveCategory(CodeEnumMixin, str, Enum):
    """
    在保责任-五级分类（liabInfo.fiveCate）。
    """

    NORMAL = "1"  # 正常
    ATTENTION = "2"  # 关注
    SUBSTANDARD = "3"  # 次级
    DOUBTFUL = "4"  # 可疑
    LOSS = "5"  # 损失
    UNCLASSIFIED = "9"  # 未分类


class CompAdvFlag(CodeEnumMixin, str, Enum):
    """
    代偿(垫款)标志（liabInfo.compAdvFlag）。
    """

    NO = "0"  # 否
    YES = "1"  # 是


class OverdueAcctType(CodeEnumMixin, str, Enum):
    """
    逾期催收-账户类型（acctType）。
    """

    NON_REVOLVING_LOAN = "D1"  # 非循环贷账户
    REVOLVING_LOAN = "R1"  # 循环贷账户
    CREDIT_CARD = "R2"  # 贷记卡账户
    QUASI_CREDIT_CARD = "R3"  # 准贷记卡账户
    SUB_ACCOUNT_UNDER_REVOLVING_LIMIT = "R4"  # 循环额度下分账户
    COLLECTION_ACCOUNT = "C1"  # 催收账户


class OverdueBusinessLine(CodeEnumMixin, str, Enum):
    """
    逾期催收-借贷业务大类（busiLines）。
    """

    LOAN = "1"  # 贷款
    CREDIT_CARD = "2"  # 信用卡
    SECURITIES_FINANCING = "3"  # 证券类融资
    FINANCIAL_LEASING = "4"  # 融资租赁
    ASSET_DISPOSAL = "5"  # 资产处置
    ADVANCE_PAYMENT = "6"  # 垫款


class OverdueBusinessDetailLine(CodeEnumMixin, str, Enum):
    """
    逾期催收-借贷业务种类细分（busiDtlLines）。
    仅沉淀当前联调高频值，可按文档继续扩展。
    """

    # 贷款
    PERSONAL_HOUSING_COMMERCIAL_LOAN = "11"  # 个人住房商业贷款
    PERSONAL_COMMERCIAL_HOUSING_LOAN = "12"  # 个人商用房（含商住两用）贷款
    PERSONAL_HOUSING_FUND_LOAN = "13"  # 个人住房公积金贷款
    PERSONAL_AUTO_CONSUMPTION_LOAN = "21"  # 个人汽车消费贷款
    PERSONAL_STUDENT_LOAN = "31"  # 个人助学贷款（国家/商业助学不可区分时填报）
    NATIONAL_STUDENT_LOAN = "32"  # 国家助学贷款
    COMMERCIAL_STUDENT_LOAN = "33"  # 商业助学贷款
    PERSONAL_OPERATION_LOAN = "41"  # 个人经营性贷款
    FARMER_LOAN = "51"  # 农户贷款（经营/消费性农户不可区分时填报）
    OPERATION_FARMER_LOAN = "52"  # 经营性农户贷款
    CONSUMPTION_FARMER_LOAN = "53"  # 消费性农户贷款
    OTHER_PERSONAL_CONSUMPTION_LOAN = "91"  # 其他个人消费贷款
    OTHER_LOAN = "99"  # 其他贷款

    # 信用卡
    QUASI_CREDIT_CARD = "71"  # 准贷记卡
    LOAN_CARD = "81"  # 贷记卡
    LARGE_INSTALLMENT_CARD = "82"  # 大额专项分期卡

    # 证券类融资
    SECURITY_REPO = "61"  # 约定购回式证券交易
    STOCK_PLEDGE_REPO = "62"  # 股票质押式回购交易
    MARGIN_TRADING = "63"  # 融资融券业务
    OTHER_SECURITIES_FINANCING = "64"  # 其他证券类融资

    # 融资租赁
    FINANCIAL_LEASING = "92"  # 融资租赁业务

    # 资产处置
    ASSET_DISPOSAL_DEBT = "A1"  # 由资产处置机构处置的债务

    # 垫款
    ADVANCE_DEBT = "B1"  # 因代偿继承债权的债务


class DisbursementFlag(CodeEnumMixin, str, Enum):
    """
    分次放款标志（flag）。
    """

    ONE_TIME = "0"  # 贷款额度一次性发放
    SPLIT_MULTI_ACCOUNT = "1"  # 分次发放，且每笔放款对应独立 D1 账户
    SPLIT_SINGLE_ACCOUNT = "2"  # 分次发放，且所有放款汇总在同一 D1 账户


class RepayMode(CodeEnumMixin, str, Enum):
    """
    还款方式（repayMode）。
    """

    INSTALLMENT_EQUAL_PI = "11"  # 分期等额本息
    INSTALLMENT_EQUAL_PRINCIPAL = "12"  # 分期等额本金
    INTEREST_INSTALLMENT_PRINCIPAL_DUE = "13"  # 到期还本分期结息
    PROGRESSIVE_RATIO_INSTALLMENT = "14"  # 等比累进分期还款
    PROGRESSIVE_EQUAL_INSTALLMENT = "15"  # 等额累进分期还款
    OTHER_INSTALLMENT = "19"  # 其他类型分期还款
    PRINCIPAL_INTEREST_AT_MATURITY = "21"  # 到期一次还本付息
    PREPAID_INTEREST_PRINCIPAL_DUE = "22"  # 预先付息到期还本
    REPAY_ANYTIME = "23"  # 随时还
    OTHER_NON_INSTALLMENT = "29"  # 其他类型非分期还款
    R1_PRINCIPAL_DUE = "31"  # 按期结息，到期还本
    R1_FREE_PRINCIPAL = "32"  # 按期结息，自由还本
    R1_CALCULATED_PI = "33"  # 按期计算还本付息
    R1_OTHER = "39"  # 循环贷款下其他还款方式
    SUMMARY = "90"  # 汇总报送，不区分还款方式


class RepayFrequency(CodeEnumMixin, str, Enum):
    """
    还款频率（repayFreqcy）。
    """

    DAY = "01"  # 日
    WEEK = "02"  # 周
    MONTH = "03"  # 月
    QUARTER = "04"  # 季
    HALF_YEAR = "05"  # 半年
    YEAR = "06"  # 年
    ONE_TIME = "07"  # 一次性
    IRREGULAR = "08"  # 不定期
    TEN_DAY = "12"  # 旬
    BI_WEEK = "13"  # 双周
    BI_MONTH = "14"  # 双月
    OTHER = "99"  # 其他


class OverdueGuarMode(CodeEnumMixin, str, Enum):
    """
    担保方式（guarMode，逾期接口）。
    """

    PLEDGE = "1"  # 质押
    MORTGAGE = "2"  # 抵押
    ASSURANCE = "3"  # 保证
    CREDIT = "4"  # 信用/免担保
    COMBINATION_WITH_ASSURANCE = "5"  # 组合（含保证）
    COMBINATION_WITHOUT_ASSURANCE = "6"  # 组合（不含保证）
    FARMER_JOINT = "7"  # 农户联保


class OthRepyGuarWay(CodeEnumMixin, str, Enum):
    """
    其他还款保证方式（othRepyGuarWay，逾期接口）。
    """

    NONE = "0"  # 无
    DEPOSIT = "1"  # 保证金
    OTHER = "9"  # 其他


class AssetTrandFlag(CodeEnumMixin, str, Enum):
    """
    资产转让标志（assetTrandFlag）。
    """

    NO = "0"  # 否
    YES = "1"  # 是


class FundSource(CodeEnumMixin, str, Enum):
    """
    资金来源（fundSou）。
    """

    SELF_OPERATED = "1"  # 自营
    ENTRUSTED = "2"  # 委托（不能区分委托类型时填报）
    GOV_ENTRUSTED = "21"  # 政府部门委托
    ENTERPRISE_ENTRUSTED = "22"  # 企事业单位委托
    PERSONAL_ENTRUSTED = "23"  # 个人委托
    HOUSING_FUND_CENTER_ENTRUSTED = "24"  # 住房公积金管理中心委托
    TRUST = "4"  # 信托
    JOINT = "8"  # 联合


class FirstHouLoanFlag(CodeEnumMixin, str, Enum):
    """
    是否为首套住房贷款（firstHouLoanFlag）。
    适用条件：
    - 适用于 D1 类账户
    - 且借贷业务种类细分 = 11（个人住房商业贷款）
    """

    YES = "01"  # 是
    NO = "02"  # 否
    UNKNOWN = "03"  # 未知
    POLICY_NOT_PUBLISHED = "04"  # 未发布差别化住房信贷政策


class ImagingDocCode(CodeEnumMixin, str, Enum):
    """
    影像资料码值（iDocList.docCde）。
    文件命名约定见 filename_by_code。
    """

    ANNUAL_SALES_AGREEMENT = "12001"  # 《年销协议》-卖方&买方
    MAXIMUM_LIMIT_CONTRACT = "12002"  # 《应收账款转让最高额度合同》+《买方账款最高子额度合同》
    ACCOUNTS_PAYABLE_CONFIRMATION = "12003"  # 《应付账款确认书》-买方
    ACCOUNTS_RECEIVABLE_CONFIRMATION = "12004"  # 《应收账款确认书》-卖方
    FACTORING_FINANCING_VOUCHER = "12005"  # 保理商发放保理融资款凭证
    COMPENSATION_VOUCHER = "12006"  # 代偿凭证
    OVERDUE_NOTIFICATION = "12007"  # 保理商向买方发送的逾期短信通知
    OVERDUE_COMPENSATION_INFORMATION = "12008"  # 担保人向买方发送的逾期代偿信息
    BAD_CREDIT_REPORT_NOTIFICATION = "12009"  # 担保人向买方发送的上报不良信息告知短信

    @classmethod
    def filename_by_code(cls, code: str) -> str:
        mapping = {
            cls.ANNUAL_SALES_AGREEMENT.value: "annual_sales_agreement",
            cls.MAXIMUM_LIMIT_CONTRACT.value: "maximum_limit_contract",
            cls.ACCOUNTS_PAYABLE_CONFIRMATION.value: "accounts_payable_confirmation",
            cls.ACCOUNTS_RECEIVABLE_CONFIRMATION.value: "accounts_receivable_confirmation",
            cls.FACTORING_FINANCING_VOUCHER.value: "factoring_financing_voucher",
            cls.COMPENSATION_VOUCHER.value: "compensation_voucher",
            cls.OVERDUE_NOTIFICATION.value: "overdue_notification",
            cls.OVERDUE_COMPENSATION_INFORMATION.value: "overdue_compensation_information",
            cls.BAD_CREDIT_REPORT_NOTIFICATION.value: "bad_credit_report_notification",
        }
        return mapping.get(code, "unknown_attachment")


class LoanForm(CodeEnumMixin, str, Enum):
    """
    放款形式（loanForm）。
    """

    NEW_ADD = "1"  # 新增
    OTHER_INSTITUTION_TRANSFER = "5"  # 其他机构转入
    OTHER = "9"  # 其他


class OrigDebtCategory(CodeEnumMixin, str, Enum):
    """
    原债务类别（origDbtCate）。
    """

    PERFORMING = "10"  # 正常类
    SPECIAL_MENTION = "20"  # 关注类
    SUBSTANDARD = "30"  # 次级类
    DOUBTFUL = "40"  # 可疑类
    LOSS = "50"  # 损失类


class InitRepayStatus(CodeEnumMixin, str, Enum):
    """
    初始还款状态（initRpySts）。
    """

    NORMAL = "1"  # 正常
    OVERDUE = "2"  # 逾期
    DEFAULT = "3"  # 违约


class OverdueAcctStatus(CodeEnumMixin, str, Enum):
    """
    非货币履约信息-账户状态（nonMonPerf.acctStatus）。
    """

    NORMAL = "1"  # 正常
    CLOSED = "2"  # 关闭
    OVERDUE = "3"  # 逾期


class RepayStatus(CodeEnumMixin, str, Enum):
    """
    非货币履约信息-还款状态（nonMonPerf.rpystatus）。
    """

    NORMAL = "1"  # 正常
    OVERDUE = "2"  # 逾期
    BAD_DEBT = "3"  # 呆账/坏账
