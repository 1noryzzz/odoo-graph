# Telemetry 观察报告（2026-08-31）

对照基线：[../1.7-Event_Tracking/telemetry-report-2026-06-25.md](../1.7-Event_Tracking/telemetry-report-2026-06-25.md)（1.8 `context` 发布前）。  
机器可读快照：[telemetry-report-2026-08-31.json](./telemetry-report-2026-08-31.json)。  
逐次调用表：[odoo_graph_usage.csv](./odoo_graph_usage.csv)（本机 telemetry 导出，列对齐 1.7 的 `codex_odoo_graph_usage.csv`）。  
1.8 设计：[context-command-design.md](./context-command-design.md)。

## 范围

- **只统计** 本机 `~/.cache/odoo-graph/telemetry.sqlite3` 的 `cli_invocations`。
- **不纳入**：Aliyun RDS / 线上 Odoo 库、本机 Postgres 里实际存在但未出现在 telemetry 中的库、dump 缓存目录的修改时间。dump 缓存未必是最新图，不能当使用量或覆盖率证据。
- **窗口**：2026-06-30（1.8.0 合入）至 2026-08-31。窗口内实际写入的 1.8.0 记录是 **2026-08-21 至 2026-08-30**。2026-07 整月 **0 条**。
- Session 默认 gap：60s；敏感性见附录。
- 逐次调用原始表与 1.7 的 `codex_odoo_graph_usage.csv` 对齐前 6 列（`timestamp,session_file,cwd,command,matched_pattern,surrounding_text`）。1.7 那份来自 Codex session 抓取；本份从本机 telemetry 导出，`session_file` 为 thread id，并多了 db/client/耗时/结果列。窗口内 **58** 行，对应 1.8.0 全部记录。

## 结论（先看这个）

1. **1.8 的主目标没有被用上。** `context` 在两个月窗口里只出现 **1 次**，而且是 explicit group（一次传 4 个模型），结果 `not_found`，整组失败。没有 seed-first 调用，也没有纠正模型名后的重试。
2. **真实高频工作已经从「拼模型上下文」变成「查方法 override + 字段诊断」。** 窗口内 `overrides` 19 次、`field` 16 次，合计占查询类调用的大多数；`model` 从基线的 19/27 降到 4/58。这主要是任务形态变了（基准产品上的入驻/审批向导），**不是** `context` 替代了 `model` burst。
3. **Agent 仍在用多次单对象命令手工拼一组相关上下文。** 最大 session 18 次：同一批 wizard 上连续 `field`，再连续 `overrides`。跨模型同名字段（`credit_term` / `repay_day` / `term_days` / `product_plan_version_id`）和同流程多个方法（`confirm_merchant`、`action_confirm`）是稳定模式。`path` fan-out 仍为 0，`max_depth` / `max_paths` 升级仍为 0。
4. **加载成本仍然是查询路径的主开销。** 有 graph load 的调用 load p50 ≈ 1052ms；m3 查询 session 里 load/total ≈ 0.76，同一张图重复加载 42 次。这继续支持 Phase 2 的常驻/缓存评估，但它解决的是「同 session 连打 10+ 次」的税，不是命令粒度本身。
5. **Dump 失败全部是 `--odoo-path` 试错，不是缺缓存。** 3 次 `dump_error` 都在 `unified-production-m2`，耗时 0ms（`odoo-bin` 路径一上来就不对），随后同 session 用 `.` 成功。Skill/示例里的 `./odoo-17.0` 与这次工作目录不一致。
6. **下一步不应再默认加宽 `context` 的模型发现，除非先修「一组里缺一个就全失败」并让 agent 真的会去调用它。** 证据更支持：批量 `overrides` / 批量 `field`（含同名字段跨模型）、dump 路径纠错、以及 Phase 2 加载缓存。

下面区分 **数据支持** 与 **推测**。未拍板改 roadmap。

## 全库时间线

本机 telemetry 全量 85 条（2026-05-29 → 2026-08-30）：

| 版本 | 条数 | 时间 |
| --- | --- | --- |
| 1.7.0 | 27 | 2026-05-29 → 2026-06-25 |
| 1.8.0 | 58 | 2026-08-21 → 2026-08-30 |

按月：2026-05 = 5，2026-06 = 22，**2026-07 = 0**，2026-08 = 58。

窗口内按日：

| 日期 | 条数 | 主要命令 |
| --- | --- | --- |
| 2026-08-21 | 2 | `impact` + `field`（`ysb-dev`） |
| 2026-08-25 | 3 | `dump` ×3（`unified-production-dev`） |
| 2026-08-27 | 6 | `dump` ×6，其中失败 3（`unified-production-m2`） |
| 2026-08-28 | 12 | 开始打 m3 查询：`overrides` 6 + `field` 3 + `dump` 2 + `module` 1 |
| 2026-08-29 | 29 | 窗口峰值：`overrides` 13 + `field` 11 |
| 2026-08-30 | 6 | `model` 3 + `module` 1 + 失败的 `context` 1 + `field` 1 |

7 月空窗只说明 **telemetry 没有记录**，不能推断工具完全没用过；本报告不把 dump 缓存 mtime 补进去当调用。

## 与 2026-06-25 基线对照

| 指标 | 2026-06-25 报告（1.7） | 本窗口（1.8 起实际记录） |
| --- | --- | --- |
| invocations | 27 | 58 |
| sessions（gap 60s） | 6 | 15 |
| calls/session avg | 4.50 | 3.87 |
| calls/session p50 / p90 | 2.0 / 5 | 1 / 10 |
| 主导命令 | `model` 19 | `overrides` 19，`field` 16 |
| `context` | 无 | 1（失败） |
| `path` fan-out | 0 | 0 |
| client | local 21，codex 6 | cursor 47，codex 11 |
| format | human 21，json 5，graphviz 1 | human 57，json 1 |
| cwd | `/Users/1noryzzz/Odoo` 为主 | `/Users/1noryzzz/Odoo-unified-production` 56 / 58 |
| follow-up 同 target / 不同 target | 2 / 19 | 4 / 39 |
| load p50 | 1026ms | 1052ms |
| load/total | 0.64 | 0.53（m3 查询约 0.76） |

p50 session 降到 1，是因为 9/15 个 session 只有 `dump`；真正做业务探索的 session 仍然是 10～18 次连打。平均数被 dump-only session 拉低了，不能读成「信息密度已经够了」。

## 1.8 窗口总览（gap 60s）

- invocations：58
- first / last：2026-08-21T11:12:35.411Z → 2026-08-30T15:14:25.657Z
- sessions：15；calls/session avg 3.87，p50=1，p90=10，p95=10
- 结果：`success_non_empty` 52，`dump_error` 3，`success_empty` 2，`not_found` 1
- 命令：`overrides` 19，`field` 16，`dump` 13，`module` 4，`model` 4，`impact` 1，`context` 1
- follow-up：overall 43，same target 4，different target 39
- retry：exact 3（都是 dump 失败后换 argv），parameter 0，failure-retry 3
- expansion：depth 0，path 0，empty-result 1
- batch：multi-model session 1，multi-field session 3
- 转移矩阵头部：`overrides→overrides` 15，`field→field` 10，其余都 ≤3

## 分库（来自 argv 的 `--db` / `-d`）

窗口内出现过的库只有 telemetry 里写到的这四个。没有出现的库不统计。

### `unified-production-m3-20260828`（46 条，业务探索几乎全在这里）

- sessions 7；calls/session avg 6.57，p50=5，p90=10，p95=18
- 命令：`overrides` 19，`field` 15，`module` 4，`model` 4，`dump` 3，`context` 1
- client：cursor 45，codex 1
- follow-up 39 次 **全部是不同 target**
- load/total ≈ 0.76；同一 graph 重复加载 42 次
- 失败：仅那一次 `context` `not_found`
- 业务前缀几乎全是 `ifs.gar.*`，模块反复查 `ifs_financial_product_entry`

这是讨论迭代时应该加权最高的库：基准产品开发期间的真实 agent 探索。

### `unified-production-m2`（7 条，全是 dump）

- 全部 `dump`，codex，cwd 同为 `Odoo-unified-production`
- 3 次失败 + 同窗口成功 dump：缺 `--odoo-path`、`--odoo-path ./odoo-17.0`、`--odoo-path ./odoo` 均 0ms 失败；成功的是 `--odoo-path .`

### `unified-production-dev`（3 条，全是 dump）

- 3 次成功 dump，codex，同日连续刷新（models_count 560 → 565）。没有后续查询记录。

### `ysb-dev`（2 条）

- 2026-08-21：`impact` 然后立刻 `field`，同一 target `ifs.gar.loan.account.bill.repayment_date`。这是窗口里唯一的 same-target follow-up 查询对；`impact` 之后用 `field` 补诊断，而不是 `path`。

## 1.8 `context` 成功指标验收

设计里的预期 vs 窗口观察：

| 设计指标 | 观察 | 判定 |
| --- | --- | --- |
| `model` calls/session 下降 | 窗口 `model` 仅 4 次；含 `model` 的 session 2 个，其中 1 个仍是 3 次连续 `model` | **数量下降成立，原因不成立**：任务转到 overrides/field，不是 context 压缩了 model burst |
| 先 seed `context` 再 explicit group | seed 0，group 1 且失败 | **未出现** |
| `context` 出现在原先的 multi-model burst 里 | 唯一相关 session：`module → model ×3 → context(4 models)`，context 失败 | **形态接近但未成功替代** |
| 不同 target 的 model 探索 follow-up 下降 | 不同 target follow-up 仍是 39/43 | **未改善**；当前 follow-up 主力已是 overrides/field，不是 model |
| 缺缓存失败后能 dump 重试 | 窗口没有 missing-cache 失败；dump 失败是 odoo-path | **该项无样本** |

唯一一次 `context`（id=84，2026-08-30T15:09:19Z）：

```text
context ifs.gar.trade.order ifs.gar.payment.order
        ifs.gar.loan.account.bill ifs.gar.repayment.order
        --db unified-production-m3-20260828 -f human
→ not_found
```

实现是「任一模型缺失则整组 `KeyError`」，所以这次调用没有返回其余模型的部分关系。约 5 分钟后同 thread 只补了一次 `field ifs.gar.sub.loan.account.used_quota`，没有纠正模型名重试 `context`。

## 稳定出现的探索模式（数据支持）

### A. 方法 override 连打

最大的两个查询 session：

- 18 calls：approve/funder wizard 的 `field` 与 `overrides`（`action_confirm` / `create` / `write` / `confirm_merchant` / `_revalidate_*`）
- 10 calls：`module ifs_financial_product_entry` 之后 6 次 `overrides`（`confirm_merchant`、两个 wizard 的 `action_confirm`、三个 `_ensure/_lock/_revalidate`），再 3 次 `field`

`overrides` 的 result_size 多在 2–4（override_depth 2–4）。Agent 不是因为深度不够而升级参数，而是 **已经知道方法名，要一张相关方法清单**。同一方法跨 session 重复出现（`confirm_merchant` 3 次，两个 `action_confirm` 各 2–3 次），说明结果没有在 agent 侧沉淀，或跨 conversation 无法复用。

### B. 同模型多字段 + 同字段跨模型

- 同一 session 内 `ifs.gar.review.merchant.approve.wizard` 查 4 个字段，对应的 `funder.approve.wizard` 再查同一组字段名。
- 跨模型同名字段：`product_plan_version_id`、`credit_term`、`repay_day`、`term_days`。

这就是 1.7 设计里的 `same_model_multi_field` / `same_field_cross_model`，当时基线样本里几乎没有，本窗口已经清楚出现。

### C. 空 `field` 结果解释不足（弱信号）

两次 `success_empty`：`ifs.gar.loan.account.credit_partition_mode`、`ifs.gar.review.merchant.route.wizard.product_plan_version_id`。后者之后 empty-result expansion=1。样本量小，但空结果目前几乎不解释「为什么没有上下游」。

### D. Dump `--odoo-path` 试错

三次失败 argv：

1. `dump -c odoo.conf -d unified-production-m2`（无 `--odoo-path`）
2. `... --odoo-path ./odoo-17.0`
3. `... --odoo-path ./odoo`

成功形态是 `--odoo-path .` 或绝对路径 `/Users/1noryzzz/Odoo-unified-production`。失败 duration_total_ms=0，符合 `odoo-bin not found under ...` 的立即失败。Skill 示例仍写 `./odoo-17.0`，和这次基准产品仓库布局不一致。

## 明确没有出现的模式

- `path` 命令：窗口 **0 次**（基线也是 0 次 fan-out；基线甚至没有稳定 path 使用）。
- depth / max_paths 升级：0。
- graphviz：0（1.7 基线有 1 次失败）。
- json：仅 1 次 `field`。
- seed-first `context`：0。

因此 1.8 有意不做的 path fan-out / MCP，用本窗口数据仍然成立；但「先做 context 压缩 model 探索」这条主路径没有被真实工作流选中。

## 加载成本

有 `duration_load_ms` 的 45 次查询：avg 1050ms，p50 1052，p90 1142。查询本身 `duration_query_ms` 中位数是 0。也就是说 **CLI 冷启动读 JSONL 图 ≈ 整次调用**。

`unified-production-m3-20260828`：43 次加载，重复加载 42 次。18 次 session 大约要付 18 秒只加载、查询接近 0。这与 1.7 观察到的「burst 里反复 load」同构，只是单次 load 从当时样本的 ~2.5s 降到 ~1.0s，比例问题没变。

Dump 成功路径 3–5s（记录在 `duration_query_ms`），和查询路径的 1s load 不是同一类问题。

## 证据 vs 推测

**数据支持**

- 窗口内主导命令是 `overrides` 和 `field`，不是 `model`/`context`。
- 业务探索高度集中在 `unified-production-m3-20260828` + `ifs.gar.*` 入驻/审批流程。
- 连打模式是不同 target 的 overrides/field，不是参数升级，也不是 path fan-out。
- `context` 一次调用且失败；dump 失败是 odoo-path。
- 重复 graph load 仍占查询墙钟时间的大部分。

**推测（样本量不够或 telemetry 看不到）**

- 7 月空窗是没用、用了但没写入，还是别的 checkout/opt-out：未知。
- Agent 不调用 `context` 是因为 skill 引导偏 overrides/field、输出不够有用，还是根本不记得有这条命令：未知。只有 1 次失败样本。
- `overrides` 要不要做签名/`super()`（roadmap 2.x）：本窗口只能说明「在查 override 链」，看不出当前输出缺签名或 super。
- 调用量「应该很多」但 telemetry 只有 58 条 1.8 记录：可能是探索发生在源码/Odoo 里、只有卡点才打 odoo-graph。本报告不把这个当成功能缺失的证据。

## 下一步迭代方向（讨论稿，未实施）

按「证据强度 × 对当前 burst 的压缩」排序，供拍板：

1. **批量 `overrides`（或「从一个方法/模型展开相关 override」）**  
   直接对应 15 次 `overrides→overrides`。例如一次接受多个 `model.method`，或从模型列出带 override 的方法。这是当前最大的连打来源。

2. **批量 `field` / 同名字段跨模型**  
   对应 10 次 `field→field` 和 4 个同名字段跨 approve/funder wizard。一次输入多个 `model.field`，或 `field <field_name> --models a,b`。

3. **`context` 小修，而不是加宽发现**  
   至少：explicit group 缺模型时返回其余模型 + 缺失列表 + suggestion，不要整组 `not_found`。在 agent 几乎不调用 seed 模式的现状下，先不要做更大的自动扩图。

4. **Dump `--odoo-path` 纠错**  
   找不到 `odoo-bin` 时给出 cwd 下的候选路径（`.`、`./odoo`、上次成功 dump 的路径），不要让 agent 连试三次 0ms 失败。顺手把 skill 示例从写死的 `./odoo-17.0` 改成「工作区里实际有 `odoo-bin` 的根」。

5. **Phase 2：同 process / MCP 内缓存图**  
   load 仍是 ~1s × 连打次数。优先服务「一个 session 里 10+ 次 overrides/field」，而不是先做远程协议。若只做 CLI，进程内 cache 或常驻查询也比新命令更能砍墙钟时间。

暂缓（本窗口没有新证据）：

- path 批量 / fan-out
- 默认 depth/paths 调整
- 把 `context` 做成更大的局部子图命令（在调用率≈0 且 fail-closed 未修之前）
- 用线上 RDS 或 dump 目录完整性来倒推功能缺口

## 附录：窗口 human report（gap 60s）

```text
Telemetry Report
================
gap seconds: 60
invocations: 58
first invocation: 2026-08-21T11:12:35.411Z
last invocation: 2026-08-30T15:14:25.657Z
sessions: 15
calls/session avg: 3.87
calls/session p50/p90/p95: 1 / 10 / 10

Client frequency:
  cursor: 47
  codex: 11

Command frequency:
  overrides: 19
  field: 16
  dump: 13
  module: 4
  model: 4
  impact: 1
  context: 1

Follow-up:
  overall: 43
  same target: 4
  different target: 39

Path fan-out:
  groups: 0

Batch exploration:
  multi-model sessions: 1
  multi-field sessions: 3

Load overhead:
  load ms avg/p50/p90: 1050.20 / 1052 / 1142
  load/total ratio: 0.53

Gap sensitivity:
  30s: sessions=16 p50=1.5 p90=10
  60s: sessions=15 p50=1 p90=10
  120s: sessions=14 p50=1.5 p90=11
```
