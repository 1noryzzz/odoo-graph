### 模块功能

* PRD: https://oabay.netlify.app/prd/prd_v1.0.html
* DB 表结构：https://www.processon.com/view/link/69c133975491e91488de6ce5
* HY 接口文档：
    HY提供的版本：https://c1wtozgfsxd.feishu.cn/docx/XNxndeeW5o5Tgrxvb3qcSqzrnOf
    添加内部说明的版本：https://fcnie0e3wzde.feishu.cn/wiki/VuUkwied2iRkipkHhRqc93qjnzh

- 催收管理
    - 催收单据在保理账单日切（定时任务）时生成
    - 展期合同模板 t24_contract_template.xml

### 基础信息接口调试（昊悦征信）
- 前置接口：后续接口中使用的个人信息，均需要先通过征信查询接口获取
    提供了一个Java版本的示例：addons-oabay/ifs_gar_post_loan_manage/ReportController.java
        - RSA+AES混合加密
        - application/json
    测试页面：http://manage-test.oabay.com/tool/report   （帐号密码：admin/admin123）
    * HY 个人征信查询接口文档：https://c1wtozgfsxd.feishu.cn/wiki/Pd9SwKCwBiWqGqkc1OncWjfTn5e
    
- 调试脚本：`test_credit_basic_info_api.py, test_guarantee_info_api.py, test_overdue_info_api`
    目前仅验证接口调用成功，未实现相关业务逻辑
- 枚举配置：`credit_enums.py`
- SFTP 配置： `sftp_utils.py`
- 当前调试策略：
  - 仅做最小成功判定：响应存在 `retCode`、`retMsg`


### 模块使用者：催收单据上的操作（签署展期/发起保理/发起代偿/等级坏账）由保理方发起
- 签署展期合同流程（双方确认后在系统中点击按钮完成逻辑）

    > 签署展期 签署双方是 保理方和采购方（买方）
        注：部分业务文档可能表述为保理方与资金方，但根据展期合同模板 (T24) 定义，签署方为买方与保理商。
        签署流程逻辑：
        1. 前置条件：
            - 已在系统中创建代码为 `T24` 的展期合同模板。
            - 催收单关联的账单状态为 `overdue`（逾期）。
        2. 触发：
            - 在“催收详情”表单视图中点击“签署展期”按钮。
        3. 获取签署人签名：
            - **保理方 (Partner Two)**：
                - 数据源：直接从账单关联的保理方获取 (`bill.factor_id`)。
                - 字段：`signature`。
            - **采购方 (Partner One)**：
                - 数据源：直接从账单关联的采购方获取 (`bill.merchant_id`)。
                - 字段：`signature`。
        4. 生成合同 (`ifs.contract.info`)：
            - 前置校验：校验当前催收单是否已展期 (`is_rollover`)，若已展期则直接返回无需重复操作的提示。
            - **模板检索**：通过 `self.env["ifs.contract.template"].retrieve_by_code("T24", bill.factor_id.id, bill.supplier_id.id)` 获取。
            - **参数准备 (params)**：构造 JSON 字符串，包含展期关键要素：
                - `t24_contract_code`: T24 逾期账单展期合同流水号
                - `bill_code`: 逾期账单编号
                - `bill_amount`: 账单金额
                - `bill_cycle`: 账单周期
                - `bill_day`: 账单日
                - `repayment_day`: 还款日：默认在现有基础上 +15天
            - **记录创建**：
                - `name`: 模板名称
                - `partner_one`: 采购方引用 (例: `ifs.partner.merchant,1`)
                - `partner_two`: 保理方引用 (例: `ifs.partner.factor,1`)
                - `template_id`: T24 模板 ID
                - `params`: 准备好的 JSON 参数
                - `partner_one_signature`: 写入采购方已存留的电子签名
                - `partner_two_signature`: 写入保理方已存留的电子签名
        5. 发起签约流程：
            - 调用 `bill_id.t24_contract_info_id.signature_all()` 或 `_contract_sign()`。
            - 内部调用 `_gentleman_signing` (君子签) 完成第三方电子签约。
        6. 状态跟踪：
            - 将生成的合同记录关联到账单的 `t24_contract_info_id` 字段。
            - 定时任务 `jzq_refresh_commit_contract_cron` 将自动轮询君子签状态并同步回系统。

        ### 相关函数调用链路参考
        - **入口函数**：`addons-oabay/ifs_gar_post_loan_manage/models/ifs_gar_collection_order.py` -> `action_sign_rollover`
        - **合同生成参考**：`addons-oabay/ifs_gar_contract/models/ifs_gar_loan_account_bill.py`#L257-L286 (参考 C10 合同生成逻辑)
        - **签约核心函数**：`addons-oabay/ifs_contract_sign_jzq/models/ifs_contract_info.py`
            - `_contract_sign`: 组织签署人信息并调用签约。
            - `_gentleman_signing`: 调用君子签 API 进行申请签署。
        - **状态同步**：`jzq_refresh_commit_contract` 轮询第三方签约结果。

- 保理放款流程
    由外部接口触发，分为两步
        0. 保理业务人员确认需要保理放款后，在系统中点击“发起保理”按钮，保理放款状态更改为“已发起”
        1. 筛选保理放款状态为“已发起”但“未完成”的单据，并返回单据相关信息
        2. 保理资金处理完成后再次调用接口更新付款状态
        * 需要注意的是，调用接口的公司系统为vb因此可能无法处理复杂的token和api，可能需要auth="public"的接口，是否有办法保证数据安全？

    前置准备：
        保理放款详情 以tab页的形式展示在催收单据form页中，一条催收单据可能对应多次放款此处应该是one2many的关系
        保理放款详情需要新增一个模型来记录，字段包括：
            保理方：催收单ifs.gar.collection.order -关联账单bill_id 中获取
            供应方：催收单ifs.gar.collection.order -关联账单bill_id 中获取
            保理金额：接口传入
            业务时间：接口传入
            付款公司：保理方计算字段或related字段
            付款帐号：保理方计算字段或related字段
            收款公司：供应方计算字段或related字段
            收款帐号：供应方计算字段或related字段

    接口详情参考PRD文档中的 “查询付款申请单”和“更新付款申请单”
    - 接口1：
        查询付款申请单：此处付款申请单实际为催收的单据，筛选保理放款状态为“已发起”但“未完成”的单据。

        入参：
            - 项目编码 project_code：调用方提供
            - 业务日期 request_date：暂定为当前日期
        返回：
            参数名 	参数说明 	是否必输 	值说明
            transaction_code 逾期单据编码 是
            project_code 	项目编码 	是 	业务系统项目编码：调用方提供
            request_date 	业务日期 	是 	暂定为当前日期
            business_details 	业务详情 	是 	业务详情列表
                fact_name 	业务详情.保理公司 	是 	逾期单对应账单的保理方
                payment_info 	业务详情.付款信息 	是 	付款信息
                    payment_time 	业务详情.付款信息.付款日期 	是 	暂定为当前日期
                    fact_amount 	业务详情.付款信息.保理金额 	是 	暂定逾期单据的待还金额
                    deduction_amount 	业务详情.付款信息.扣款金额 	是 	暂定逾期单据的待还金额
                    request_pay_amount 	业务详情.付款信息.付款金额 	是 	暂定逾期单据的待还金额
                    payer_account 	业务详情.付款信息.付款账号 	是 	保理方相关信息，下同
                    payer_company 	业务详情.付款信息.付款公司 	是 	
                    payer_bank 	业务详情.付款信息.付款银行 	是 	    
                    payee_account 	业务详情.付款信息.收款账号 	是 	逾期单对应账单的供应方相关信息，下同
                    payee_company 	业务详情.付款信息.收款公司 	是 	
                    payee_bank 	业务详情.付款信息.收款银行 	是 	
                    payment_currency 	业务详情.付款信息.支付货币 	是 	默认CNY
                    payment_type 	业务详情.付款信息.支付方式 	是 	    暂定银行转帐
                buyer_name 	业务详情.买方名称 	是 	
                contract_info 	业务详情.合同信息 	是 	合同信息列表  
                    contract_name 	业务详情.合同信息.合同名称 	是 	采购方的确认书T20
                    url 	业务详情.合同信息.url 	是 	           需要获取 Aliyun OSS的url

    - 接口2：更新付款申请单：更新催收单据的"保理放款状态"为“已放款”
        更新逾期单据保理放款状态；同时根据逾期单据编码创建一条保理放款记录，关联到逾期单据上。；
        入参：
            transaction_code  	String 	逾期单据编码
            payment_time 	String 	付款日期
            actual_payment_amount 	String 	实付金额
            payment_voucher 	Number 	付款凭证
        返回：
            transaction_code  逾期单据编码