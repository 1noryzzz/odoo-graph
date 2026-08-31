---
name: odoo-graph-runtime-probe
description: 指导 AI 在 Odoo 开发中何时使用 odoo-graph 运行时探针工具，并正确选择命令（含 path 起点-终点查询）与解读输出。
---

# odoo-graph-runtime-probe

## 适用场景（何时应使用）
当用户的问题属于“运行时真实合并结果”而不是“源码静态猜测”时，优先使用 `odoo-graph`：

1. **字段影响分析**：修改某字段后会触发哪些 compute / depends 链。
2. **字段来源追踪**：字段由哪个模块定义、被哪些模块扩展，最终有效来源字段是什么。
3. **模型继承结构**：`_inherit / _inherits / mixin` 合并后实际结构。
4. **方法 override 链**：同名方法在多模块中的 MRO 顺序。
5. **seed-first 上下文探索**：只知道一个模型、需要一次性发现相关继承/委托/关系模型时，使用 `context` 命令。
6. **起点到终点的路径证明**：想证明某业务对象是否能影响目标字段（`path` 命令）。
7. **委托继承字段诊断**：字段在当前模型 `_fields` 可见、可通过 `write()` 更新，但可能真实来自 `_inherits` 父模型且不在当前模型 SQL 表中。
8. **工具使用情况分析**：用户想了解 agent 对 `odoo-graph` 的调用模式、是否存在反复查询、fan-out 或批量探索时，使用 telemetry report。

> 判断原则：如果问题明确涉及“模块叠加后最终行为”，就应使用本工具。

## 不适用场景
- 纯 Python 语法问题、与 Odoo registry 无关的问题。
- 用户只要高层概念介绍、不需要证据链。
- 尚无可用数据库或无法启动 Odoo，但用户也不允许准备环境。

## 使用前检查
1. 已有可启动的 Odoo 环境（源码、依赖、Postgres、目标 DB）。
2. `odoo-graph` 可执行。
3. 优先复用 `odoo.conf`，避免漏参数。
4. 优先扫描缓存根目录 `~/.cache/odoo-graph/`，读取已存在的 DB 子目录作为候选列表。
5. 明确当前要分析的数据库名（`--db` 或 `ODOO_GRAPH_DB`）；如用户未给且存在多库可能，必须先询问用户。

## 标准流程（默认缓存优先）
1. **先列出缓存候选 DB**：扫描 `~/.cache/odoo-graph/` 下的子目录并展示给用户。
2. **若用户已指定 DB 且缓存存在**：直接基于该缓存分析。
3. **若用户未指定 DB**：让用户从缓存候选中选择；若都不合适，再进入 dump 选项。
4. **仅在必要时触发 dump**：无缓存、缓存过旧、或用户明确要求刷新时才建议 dump。
5. **dump 前先提醒并确认**：告知用户 dump 可能与本地正在运行的 Odoo 服务产生冲突/失败风险，先征求确认。
6. **query 可多次复用**：所有查询离线读取缓存，不再启动 Odoo。
7. 输出格式仅使用 `-f human` 或 `-f json`：给人看优先 `human`，需要脚本处理时用 `json`。
8. 业务查询默认会写入本地 telemetry；除非用户要求分析工具使用情况，不要把 telemetry report 混入业务问题回答。

---

## 命令清单：何时用、输入、输出

### 0) dump
```bash
odoo-graph dump -c odoo.conf -d <db>
```
**何时用**：首次分析、数据库升级后、模块安装/升级后、或用户要求刷新缓存。  
**前置动作**：先确认目标 DB，再提醒潜在冲突并征求用户确认。  
**输出**：`~/.cache/odoo-graph/<db>/` 下的 `nodes.jsonl / edges.jsonl / edges_resolved.jsonl / summary.json / meta.json`。

默认按 `.`、`./odoo`、`./odoo-17.0`、`../odoo`、`../odoo-17.0`
的固定顺序发现直接包含 `odoo-bin` 的源码根。仅在自动发现不适用时显式传
`--odoo-path /path/to/odoo`；`ODOO_PATH` 和 CLI 显式值无效时不会回退。
`meta.json` 中的 `generated_at`、`odoo_path`、`cwd` 和
`package_version` 应作为缓存来源核对依据，但 1.9.1 不自动判定缓存过期。

### 1) field
```bash
odoo-graph field <model.field> [<model.field> ...] --db <db>
```
**何时用**：看某字段上下游依赖、字段来源、委托链、可写性原因。  
**输出**：该字段的 upstream/downstream 关系与统计；human/json 中包含 `analysis`：
- `kind`: `local / related / computed / delegated / delegated_related`
- `declared_on_model`: 是否当前模型直接声明
- `source_field`: 沿 depends/related 链追踪到的最终有效来源字段
- `writable` + `writable_reason`: 是否可通过 ORM 写入及原因
- `delegation_chain`: `_inherits` 逐跳链路，含 `via_field`、`path`、`source_field`
- `shadowing`: 同名 delegated parent field 的覆盖/遮蔽风险

已知多个字段时应在一次调用中传入，避免重复加载同一图。两个及以上目标返回
`field_batch`，每项独立标记 `found/not_found`；最多 50 项。

### 2) model
```bash
odoo-graph model <model> --db <db>
```
**何时用**：看模型继承图、字段集合、按模块归属，尤其是 `_inherits` 链式委托结构。  
**输出**：模型结构摘要、字段分组，以及完整 `delegation_chain`。

### 3) module
```bash
odoo-graph module <module_name> --db <db>
```
**何时用**：审计模块贡献（定义/扩展了什么）。  
**输出**：该模块涉及的模型、字段、方法等。

### 4) context
```bash
odoo-graph context <model> [<model> ...] --db <db>
```
**何时用**：agent 只知道一个 seed 模型、正在手工连续调用多个 `model` 命令拼上下文时，优先用它压缩探索；当已经知道模型集合时，可传入多个模型解释组内关系。
**输出**：请求模型摘要、继承/委托/关系边、`suggested_context_models`，以及单 seed 模式下建议的 follow-up 命令。显式组内部分模型缺失时读取 `result=partial`、`selected_models` 和 `missing_models` 后继续使用有效结果；只有 `result=not_found` 才表示全部目标无效。

### 5) impact
```bash
odoo-graph impact <model.field> --db <db> --max-depth 2
```
**何时用**：改动评估、回归范围评估。  
**输出**：BFS 下游影响节点（按深度）。

### 6) path（重点）
```bash
odoo-graph path <start_node> <target_node> --db <db>
```
示例：
```bash
odoo-graph path child.record res.partner.name --db odoo_demo
```
**何时用**：需要“可达性证据链”时（从业务起点到目标字段）。  
**输出**：一条或多条从起点到终点的路径（节点序列 + 边关系）；不可达时明确无路径。

### 7) overrides
```bash
odoo-graph overrides <model.method> [<model.method> ...] --db <db>
```
**何时用**：排查方法调用链、super 顺序争议。  
**输出**：跨模块 override 顺序（按 MRO 展示）。已知多个方法时放入一次调用；
两个及以上目标返回 `overrides_batch`，保持输入顺序并复用一次图加载，最多 50 项。

### 8) telemetry
```bash
odoo-graph telemetry report
```
**何时用**：用户明确要求查看 `odoo-graph` 使用情况、agent 调用模式、session 内多次查询、fan-out、批量探索或加载耗时时。  
**输出**：本地 SQLite telemetry 的后处理与分析报告，包括 first/last invocation、session 调用次数、命令频率、top targets、top sessions、command sequence、failure details、format / cwd / db / out-dir 使用分布、follow-up、retry、参数升级、`path` fan-out、批量 model / field 探索、graph source load stats、load overhead，以及 30s / 60s / 120s gap 敏感性分析。

相关命令：

```bash
odoo-graph telemetry init
odoo-graph telemetry report -f json
```

默认 telemetry DB：`~/.cache/odoo-graph/telemetry.sqlite3`。可用 `ODOO_GRAPH_TELEMETRY_DB` 覆盖路径；单次业务命令可加 `--no-telemetry`，或用 `ODOO_GRAPH_TELEMETRY=0` 关闭采集。

---

## 输出解读规则（给 AI 的行为约束）
1. **先报结论，再报证据**：结论必须绑定具体命令输出。
2. **区分“无结果”与“无数据”**：
   - 无结果：图里查到但关系为空（例如 no path）。
   - 无数据：dump 过旧/失败/DB 不对。
3. **涉及风险时给下一步建议**：
   - path 不可达：建议确认起点节点命名或先跑 `field/model` 验证节点存在。
   - 影响范围过大：建议降低 `--max-depth` 或切到 `-f json` 过滤。
4. **多命令组合建议**：
   - 先 `field` 看局部；
   - 再 `impact` 看半径；
   - 最后 `path` 给可解释链路证据。
5. **遇到 `_inherits` / 代理字段 / SQL 表字段缺失争议时**：
   - 不要只用数据库表结构或源码静态 grep 下结论。
   - 先跑 `odoo-graph field <model.field> --db <db>`，读取 `analysis.kind`、`source_field`、`writable_reason`、`delegation_chain`。
   - 再跑 `odoo-graph model <model> --db <db>`，确认完整模型级 `Delegation chain`。
   - 如需证明最终字段来源，再跑 `odoo-graph path <model.field> <source.model.field> --db <db>`。
   - 回答时明确区分“当前模型 registry 可见字段”和“当前模型 SQL 表物理列”。
6. **数据库参数规则**：
   - 若用户未提供 `--db` 且上下文无法唯一确定 DB，先询问再执行查询。
   - 优先给出缓存中可选 DB 列表，让用户选择。
   - 若用户提到的 DB 在缓存中存在，可直接分析并告知“正在使用缓存”。
   - 若用户不选缓存或要求最新数据，可提供“先 dump 新缓存再分析”的选项。
   - 不要擅自在多数据库环境下猜测 DB 名称。
7. **`context` 部分结果规则**：
   - `result=partial` 是可用证据，退出码为 `0`；不要因一个缺失模型丢弃已解析模型。
   - 优先根据 `missing_models[].suggestions` 修正输入，不要自动扩展大范围关系图。
8. **批量查询规则**：
   - 已知多个字段或方法时，分别使用单次 batch `field` 或 `overrides`，不要循环启动 CLI。
   - batch 的每项结果独立；部分命中是可用证据，只有全部缺失才整体失败。
   - 一次不得超过 50 项，也不要混合字段和方法到同一命令。
9. **telemetry 使用规则**：
   - 普通业务分析不需要主动运行 `telemetry report`。
   - 当用户问“这些命令用得怎么样”“agent 是否反复查询”“是否需要批量命令/缓存/daemon”时，再运行 `odoo-graph telemetry report`。
   - `--help`、`--version`、root action 和 shell 层启动失败不属于正式 telemetry 统计范围。

## `_inherits` 字段诊断回答模板
当 `field` 输出显示 `kind=delegated` 或 `kind=delegated_related` 时，回答应覆盖：

1. 字段是否当前模型直接声明：看 `declared_on_model`。
2. 最终有效来源字段：看 `source_field`。
3. 是否可写及原因：看 `writable` / `writable_reason`，尤其关注 `inverse=_inverse_related`。
4. 完整委托链：引用 `delegation_chain` 中每一跳 `from_model --via_field--> to_model`。
5. 同名覆盖风险：引用 `shadowing.risk` 和 candidates。

示例结论：

> `ifs.gar.entry.supplier.vat` 不是当前模型直接声明的本地字段；它是 `delegated_related`，最终来源是 `res.partner.vat`。当前模型可通过 ORM 写入，原因是该 related 委托字段带 `inverse=_inverse_related`。委托链是 `ifs.gar.entry.supplier --invite_id--> ifs.gar.invite.supplier --ifs_company_id--> ifs.base.company --company_id--> res.company`。因此不能仅凭 `ifs_gar_entry_supplier` 表里没有 `vat` 列判断 `write({'vat': ...})` 不可用。

## 推荐回答模板
1. 我会先列出缓存中可用 DB（若你未指定）。
2. 若你指定的 DB 在缓存中存在，我会直接用缓存分析。
3. 若你想要最新数据或缓存缺失，我会先提醒 dump 可能与运行中的 Odoo 冲突，并征求你确认。
4. 然后根据问题类型选择命令（field/model/module/impact/path/overrides）。
5. 给出简短结论，并附关键输出要点与下一步建议。
6. 若用户要求分析工具使用模式，再运行 `telemetry report` 并解释报告中的调用模式。

## 常见失败与处理
- `dump` 路径解析失败：先使用错误信息中的 `Suggested command`；仅在自动发现不适用时显式传 `--odoo-path`。
- `dump` 启动后失败：优先检查 `-c`、`-d`、DB 凭据和 addons 路径。
- 查询报找不到 DB 缓存：先确认 DB 名称是否正确，再执行 `odoo-graph dump ...`。
- `path` 无路径：检查起点/终点标识是否准确，或链路被深度/解析能力限制。
- `field` 没有显示委托链但怀疑是 `_inherits`：先跑 `model <model>` 确认是否存在 `_inherits`；若 dump 过旧或缺 `MODEL_DELEGATES_TO_MODEL` 边，需要重新 dump。
