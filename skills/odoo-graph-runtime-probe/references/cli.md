# CLI 按需参考

需要命令示例、输出字段或故障排查时读取对应小节；不要求逐项执行。参数与限额以安装版本的 `--help` 为准，以下保留既有 CLI 用法。

## 命令清单：何时用、输入、输出

### 0) dump
```bash
odoo-graph dump -c odoo.conf -d <db>
```
**何时用**：首次分析、数据库升级后、模块安装/升级后、或用户要求刷新缓存。  
**前置动作**：按 SKILL.md 的目标环境、缓存和 dump 边界执行。  
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

### 6) path
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


## 部分结果与字段解读

- `context` 的 `result=partial` 和 batch 中已命中的项目仍是可用证据；按缺失项的 suggestions 修正输入，不自动扩展整张图。
- 委托字段优先解读 `analysis.kind`、`source_field`、`writable_reason` 和 `delegation_chain`；需要模型级结构时再查 `model`，需要图内可达性时再查 `path`。
- `writable` 表示字段机制，不证明特定用户、公司和记录在当前业务状态下写入成功；权限与业务约束需要运行态证据。
- 查询通常写入本地 telemetry；`--help`、`--version` 和 shell 启动失败不属于正式业务查询统计。仅在分析工具使用情况时读取 telemetry 报告。

## 常见失败与处理

- dump 路径解析失败：检查错误中的 Suggested command；自动发现不适用时显式指定 `--odoo-path`。
- dump 启动失败：针对错误检查配置、目标 DB、凭据和 addons 路径，避免输出秘密值。
- 缓存缺失或来源不匹配：回到 SKILL.md 的缓存与 dump 判断，不直接切换数据库。
- path 无路径：核实两端节点、查询深度和图覆盖范围；不据此断言业务中不存在调用路径。
- 委托链缺失：按需查 model，判断是否是旧 dump 或缺少委托边，再决定是否刷新。
