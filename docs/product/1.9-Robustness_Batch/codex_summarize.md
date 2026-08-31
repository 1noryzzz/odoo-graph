按约 2026-08-17 至 08-31 能检索到的 `unified-production` 项目对话，核心结论是：

`odoo-graph` 主要用于回答“所有 addon 加载完成后，Odoo registry 的最终语义是什么”，而不是替代源码搜索、SQL 或业务测试。

| 场景 | 试图确认的信息 |
|---|---|
| M1 Product Plan / Version | `_inherit`、`_inherits` 后字段到底归属哪个模型；字段是否本地持久化、是否只是委托字段。比如 Entry 的 `factor/funder/supplier` 是 delegated fields，不能直接当作 Entry 表字段。 |
| M2 Facade / Account Resolver | Facade、Resolver 是否真的装入 registry；AbstractModel 的扩展关系、MRO、模块依赖方向、Bill 版本锁入口是否被正确保护。一次 dump 得到 567 models、14,740 fields、5,625 override edges。 |
| M3 审批链 | `confirm_merchant`、`action_confirm` 的最终 override 顺序；Wizard 字段是否只读、是否有 inverse、是否因 `compute_sudo` 可展示。实际发现过缓存过旧的问题。 |
| M4 日切与 H5 | 源码中新拆出的 compute 或 hook，最终是否被其他 addon 覆盖；例如 `days_left` 的最终 compute 实际来自还款模块的 `_compute_last_repayment_info`，不能只依据基础模型源码判断。 |
| 跨层业务调查 | 设想采用 `field → impact → path`：先看 ORM 字段影响图，再交给 CodeGraph 找 Python 方法、Controller 和账务动作。典型问题是“修改融资金额字段是否会影响放款”。这属于已提出的标准模式，未必每次都实际跑过完整链路。 |

反复想搞清楚的内容，大致可以归纳为五类：

1. 最终模型语义：字段 lineage、`_inherit`、`_inherits`、MRO、compute、depends、related、`compute_sudo`。
2. 字段的真实存储位置：registry 可见字段对应哪张物理表、哪一列，还是根本没有物理列。
3. 业务链路影响范围：字段变化如何连接到 Bill、额度、审批、放款、还款和 API。
4. 代码与目标数据库是否一致：模块是否 installed、registry cache 是否对应当前代码和目标库。
5. 改动是否会破坏架构边界：是否产生循环依赖、重复写路径、错误的公开 hook 或错误的版本 fallback。

目前形成的工具边界是：

- `odoo-graph`：有效 registry、字段关系、继承合并、MRO、override。
- CodeGraph：普通 Python 调用关系、方法体和执行路径。
- DB/Odoo shell：真实记录、ACL、公司隔离、cron、物理 schema。
- 日志和测试：实际执行、并发、事务回滚、外部接口结果。

尤其明确了两条安全规则：

- 旧 graph cache 不能当作当前代码证据；模块升级后应刷新目标数据库对应的 dump，并记录数据库、源码版本和生成时间。
- 提供具体 SQL 前，不能只凭 `odoo-graph` 判断列名；必须再核对真实物理表和数据列。无法连接数据库时，只能提供待核验模板。

如果把这些对话提炼成 `odoo-graph` 的产品需求，最有价值的方向是：增加 cache provenance/freshness、模型/字段/MRO 一体化输出、字段物理存储映射、两个 registry snapshot 的差异比较，以及可供 CodeGraph 接力的 JSON 化 `impact/path` 结果。核心仍应保持为 registry 语义探针，不需要扩展成业务执行器。
