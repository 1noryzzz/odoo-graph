# Agent CLI 埋点设计

## 背景

`odoo-graph` 当前主要以 Python CLI 的形式提供查询能力，主要调用方是 AI agent。下一阶段希望让工具对 agent 更友好、更高效：减少为了补齐上下文而连续调用多个子命令的情况，并为后续设计更粗粒度、更高信息密度的命令提供依据。

本设计聚焦本地个人使用场景：开发者自己开发、自己运行、自己统计，因此查询对象可以直接记录 raw name，不做匿名化；存储方式直接使用 SQLite，不再维护 JSON/NDJSON 作为主存储格式。

## 目标

埋点要回答的核心问题是：

> Agent 在一个 task / turn 内，为了获取足够上下文，是否发生了多次 CLI 查询；如果发生，识别它是因为目标解析失败、默认深度不足、单命令上下文不足、空结果解释不足，还是命令粒度太细。

具体希望识别的原因包括：

1. **目标解析失败**：target 写错、拆分失败、找不到模型/字段/方法/模块，后续通过相似 target 重试。
2. **默认深度不足**：同命令、同 target 递增 `max_depth`，或路径查询递增 `max_paths`。
3. **单命令上下文不足**：一次查询后很快对同 target 或相关 target 查询其他命令。
4. **空结果解释不足**：命令成功但结果为空，随后继续查 `model`、`module`、`field`、`path` 等上下文。
5. **命令粒度太细**：稳定出现 `field -> impact -> path`、`field -> model -> module` 等组合，说明需要更高层的组合命令或 agent profile 输出。

## 非目标

当前阶段不解决以下问题：

- 不做远程上传或多用户分析。
- 不把 JSON/NDJSON 作为主存储。
- 不匿名化查询对象名称。
- 不重点分析 DB、addons path、Odoo config 等本地固定环境信息。
- 不把“没有结果”直接视为失败。

## 存储决策

使用 SQLite 作为唯一主存储。原因：

- 需要按 thread、session、时间顺序做跨调用统计。
- 需要计算命令转移、重试、参数升级、follow-up 等关系型指标。
- SQLite 是 Python 标准库可用能力，不引入额外依赖。
- 本地单用户 CLI/MCP 写入量低，SQLite 性能和维护成本都合适。

表设计采用“一张主表 + JSON 扩展列”：

- 稳定且高频过滤/聚合的字段使用普通 columns。
- 变化大、不稳定、后续可能调整的内容放入 JSON columns：
  - `argv_json`
  - `target_meta_json`
  - `result_summary_json`
  - `extra_json`

## Session 定义

工具目前主要是 Python CLI 形态，因此通常只能获取 `CODEX_THREAD_ID`，无法稳定获取 `CODEX_TURN_ID`。

因此 session 使用以下规则推导：

1. 如果未来调用入口能提供 `CODEX_TURN_ID`，则优先使用：
   - `session_key = CODEX_THREAD_ID + ':' + CODEX_TURN_ID`
2. 当前 CLI 默认使用：
   - `session_key = CODEX_THREAD_ID + ':' + time_gap_window`
3. `time_gap_window` 通过同一 thread 内相邻调用时间差切分：
   - 相邻 invocation 间隔小于等于阈值，归为同一 session。
   - 超过阈值，开启新 session。

建议初始阈值：`60s`。后续可以根据真实调用数据调整为 `30s`、`120s` 或按命令耗时自适应。

## 需要收集的信息

### 1. 通用信息

每次 CLI 调用都记录：

- 包版本：`package_version`
- 埋点 schema 版本：`telemetry_schema_version`
- ISO 时间：`started_at`、`ended_at`
- 调用入口：`entrypoint`，当前主要为 `cli`，未来可扩展为 `mcp`
- `CODEX_THREAD_ID`：`codex_thread_id`
- `CODEX_TURN_ID`：`codex_turn_id`，当前 CLI 通常为空，保留字段方便未来 MCP 使用
- session 信息：`session_key`、`session_gap_seconds`

### 2. 单次命令信息

#### 命令与目标

- `command`：子命令名，例如 `field`、`model`、`module`、`impact`、`path`、`overrides`
- `target_raw`：主查询对象原文
- `target_kind`：`model` / `field` / `method` / `module` / `unknown`
- `target_model`：解析出的模型名
- `target_field`：解析出的字段名
- `target_method`：解析出的方法名
- `target_module`：解析出的模块名
- `start_raw`：`path` 命令的起点原文
- `start_kind`：`path` 命令起点类型
- `start_model`：`path` 起点模型
- `start_field`：`path` 起点字段

由于当前是个人本地使用，以上 raw name 直接记录，不 hash。

#### 参数

重点记录影响 agent 试探行为的参数：

- `max_depth`
- `max_paths`
- `allow_kinds`

以下内容当前不是核心维度，可以放入 `argv_json` 或 `extra_json`，不作为主分析列：

- `format`
- `quiet`
- `verbose`
- `log_level`
- `db`
- `out_dir`
- `config`
- `addons_path`

虽然当前不重点分析 `format`，但如果实际存在 `human -> json` 切换，也可以从 `argv_json` 后处理得到。

#### 执行时长

记录分阶段耗时：

- `duration_load_ms`：加载 graph / dump 数据耗时
- `duration_query_ms`：执行图查询耗时
- `duration_output_ms`：渲染和输出耗时
- `duration_total_ms`：总耗时

这些指标用于判断是否需要 daemon、MCP server 内缓存、批量查询或更高信息密度的单命令输出。

#### 执行结果

记录：

- `success`：命令是否成功执行
- `exit_code`：CLI 返回码
- `result_status`：归一化结果状态
- `error_category`：失败原因分类
- `empty_result`：成功但结果为空
- `result_size`：结果规模

`empty_result = true` 不表示失败。空结果可能是正确答案，但它是重要的输出不足信号。

建议 `result_status` 初始取值：

- `success_non_empty`
- `success_empty`
- `usage_error`
- `not_found`
- `query_error`
- `dump_error`
- `unexpected_error`

建议 `error_category` 初始取值：

- `none`
- `usage_error`
- `not_found`
- `invalid_query`
- `dump_error`
- `unexpected`

#### 查询对象上下文

变化较大，先放入 `target_meta_json`：

字段上下文：

- 字段类型，例如 `char`、`many2one`、`one2many`
- 是否计算字段：`is_compute`
- 是否 related 字段：`is_related`
- 是否 inherited / delegated 字段：`is_inherited`、`is_delegated`
- 是否有 depends：`has_depends`
- 字段来源模块：`module`

模型上下文：

- 是否 abstract model：`is_abstract`
- 是否 transient model：`is_transient`
- 是否有 `_inherit`：`has_inherit`
- 是否有 `_inherits`：`has_inherits`
- 原始模块：`original_module`

### 3. JSON 扩展信息

#### `argv_json`

保存原始参数和归一化参数形态，例如：

```json
{
  "argv": ["impact", "res.partner.name", "--max-depth", "3"],
  "arg_shape": {
    "has_max_depth": true,
    "has_max_paths": false,
    "has_allow_kinds": false,
    "format": "json"
  }
}
```

#### `target_meta_json`

保存目标对象的图上下文，例如字段类型、模型类型、继承/委托信息。

#### `result_summary_json`

保存命令相关的结果摘要，例如：

```json
{
  "upstream_count": 2,
  "downstream_count": 5,
  "primary_count_name": "downstream_count"
}
```

不同命令建议记录：

- `field`：`upstream_count`、`downstream_count`
- `model`：`extended_by_modules_count`、`fields_by_module_count`、`delegation_chain_count`
- `module`：`original_models_count`、`extended_models_count`、`original_fields_count`、`extended_fields_count`
- `impact`：`impacted_count`
- `path`：`found_paths`、`truncated`
- `overrides`：`override_depth`、`defined_in_classes_count`
- `dump`：`models_count`、`fields_count`、`resolved_count`、`unresolved_count`

#### `extra_json`

保存临时扩展内容，例如：

- suggestion 是否产生：`suggestion_emitted`
- exception type：`exception_type`
- traceback 是否截断保存：`traceback_tail`
- 实验性字段

## SQLite 数据库表结构

数据库文件建议默认放在本地 cache 目录，例如：

```text
~/.cache/odoo-graph/telemetry.sqlite3
```

### `cli_invocations`

```sql
CREATE TABLE IF NOT EXISTS cli_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    telemetry_schema_version INTEGER NOT NULL,
    package_version TEXT NOT NULL,
    entrypoint TEXT NOT NULL DEFAULT 'cli',

    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_total_ms INTEGER,
    duration_load_ms INTEGER,
    duration_query_ms INTEGER,
    duration_output_ms INTEGER,

    codex_thread_id TEXT,
    codex_turn_id TEXT,
    session_key TEXT,
    session_gap_seconds INTEGER,

    command TEXT NOT NULL,

    target_raw TEXT,
    target_kind TEXT,
    target_model TEXT,
    target_field TEXT,
    target_method TEXT,
    target_module TEXT,

    start_raw TEXT,
    start_kind TEXT,
    start_model TEXT,
    start_field TEXT,

    max_depth INTEGER,
    max_paths INTEGER,
    allow_kinds TEXT,

    success INTEGER NOT NULL,
    exit_code INTEGER,
    result_status TEXT NOT NULL,
    error_category TEXT,
    empty_result INTEGER NOT NULL DEFAULT 0,
    result_size INTEGER,

    argv_json TEXT,
    target_meta_json TEXT,
    result_summary_json TEXT,
    extra_json TEXT,

    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_cli_invocations_thread_time
    ON cli_invocations (codex_thread_id, started_at);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_session_time
    ON cli_invocations (session_key, started_at);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_command
    ON cli_invocations (command);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_target
    ON cli_invocations (target_kind, target_raw);

CREATE INDEX IF NOT EXISTS idx_cli_invocations_result
    ON cli_invocations (success, result_status, error_category);
```

### SQLite 写入建议

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 3000;
```

写入时机建议在每次 CLI 调用结束时写入一行。即使命令失败，也应该记录失败事件。若发生未捕获异常，应尽量在外层捕获并记录 `unexpected_error` 后再抛出或返回错误码。

## 分层设计

### Layer 1：单次调用事实层

直接写入 `cli_invocations` 表。包含：

- 调用时间
- thread/session 信息
- 命令与 target
- 关键参数
- 耗时
- 结果状态
- result size
- JSON 扩展信息

这是唯一必须实时写入的层。

### Layer 2：对象上下文层

先通过 `target_meta_json` 附着在单次调用上，不单独建表。

原因：

- 字段/模型上下文的稳定字段还未完全确定。
- v1 主要看调用链路，不需要立刻对对象元数据做复杂 join。
- 后续如果对象上下文稳定且查询频繁，再拆成 `target_snapshots` 表。

### Layer 3：Session 派生统计层

不实时写入。通过后处理 SQL 或分析脚本从 `cli_invocations` 计算。

派生内容包括：

- session 时长
- session invocation count
- command sequence
- follow-up rate
- retry rate
- expansion rate
- depth escalation
- path expansion
- empty result expansion

后续如果统计查询变慢或需要固化报表，可以再创建 `session_summaries` 表或 view。

## 评价指标

### 1. Task Calls Per Session

定义：每个 session 的 invocation 数量。

建议统计：

- average
- P50
- P90
- P95

目标：下降。

含义：如果一次 task 通常需要很多 CLI 调用，说明工具返回的信息密度不足，或命令粒度太细。

### 2. Follow-up Rate

定义：一次 invocation 结束后 N 秒内，同 session 内是否还有下一次 invocation。

建议拆分：

- `overall_followup_rate`
- `same_target_followup_rate`
- `different_target_followup_rate`

目标：不必要的 follow-up 下降，必要的探索仍然保留。

用于识别：

- 单命令上下文不足。
- 输出缺少下一步解释。
- Agent 需要通过额外命令补齐背景信息。

### 3. Retry Rate

定义：同一 session 内出现重复或相似查询的比例。

建议拆分：

- `exact_retry_rate`：同命令、同 target、同参数重复。
- `parameter_retry_rate`：同命令、同 target，但参数不同。
- `failure_retry_rate`：失败后再次查询。
- `target_correction_retry_rate`：失败后使用相似 target 查询。

目标：下降。

用于识别：

- target 解析或 suggestion 不足。
- 参数默认值不合理。
- 输出不够确定，导致 agent 重复确认。

### 4. Expansion Rate

定义：以某个起始命令开始后，session 内继续扩展到其他命令的概率。

按起始命令分别统计：

- `field_expansion_rate`
- `model_expansion_rate`
- `impact_expansion_rate`
- `path_expansion_rate`
- `overrides_expansion_rate`

目标：通过更丰富返回或组合命令降低不必要 expansion。

用于识别：

- 哪些命令最需要补充上下文。
- 哪些命令组合最适合升级为新命令。

## 后处理统计

以下信息不需要实时写入，可以后处理得到。

### Session 切分

按 `codex_thread_id` 和 `started_at` 排序，使用 `session_gap_seconds` 阈值切分 session，写回或临时计算 `session_key`。

### 命令序列

同一 session 内按 `started_at` 排序，得到：

```text
field -> impact -> path
model -> field
impact -> model -> module
```

用于统计命令转移矩阵和 expansion rate。

### 参数升级 / 试探模式

#### Depth escalation

同 session 内满足：

- 同 `command`
- 同 `target_raw`
- 后一次 `max_depth` 大于前一次

说明默认 depth 可能不足。

#### Path expansion

同 session 内满足：

- `command = 'path'`
- 同 `start_raw`
- 同 `target_raw`
- 后一次 `max_paths` 大于前一次

说明默认 path 数量可能不足。

#### `allow_kinds` 使用率

统计 `allow_kinds IS NOT NULL` 的比例，以及它出现在哪些命令序列中。

#### Format 切换

当前不是核心指标，但如果 `argv_json` 里保留了 format，可后处理识别 `human -> json`。

### 输出不足信号

#### Follow-up same target

同 target 调用后 N 秒内又查别的命令：

- 表示当前命令上下文可能不够。
- 需要结合命令序列判断是合理探索还是不必要 follow-up。

#### Retry after failure

失败后，同 target 或相似 target 再试：

- 表示 target 解析、错误信息或 suggestion 需要增强。

#### Empty result expansion

`empty_result = true` 后继续查询 `model` / `module` / `field` / `path`：

- 表示空结果虽然不是失败，但解释可能不足。

### 命令粒度分析

统计高频命令组合，例如：

- `field -> impact`
- `field -> impact -> path`
- `field -> model -> module`
- `impact -> path`
- `path -> field`

如果组合稳定高频，可以考虑：

- 新增组合命令。
- 在现有命令中添加 agent profile。
- 默认返回更多上下文摘要。
- 给空结果增加解释和下一步建议。

## 示例分析 SQL

### 每个 session 的调用次数

```sql
SELECT
    session_key,
    COUNT(*) AS invocation_count,
    MIN(started_at) AS started_at,
    MAX(ended_at) AS ended_at
FROM cli_invocations
GROUP BY session_key
ORDER BY invocation_count DESC;
```

### 命令使用频率

```sql
SELECT command, COUNT(*) AS n
FROM cli_invocations
GROUP BY command
ORDER BY n DESC;
```

### 同 target follow-up

```sql
SELECT
    a.command AS command_a,
    b.command AS command_b,
    COUNT(*) AS n
FROM cli_invocations a
JOIN cli_invocations b
  ON a.session_key = b.session_key
 AND b.started_at > a.ended_at
 AND b.started_at <= datetime(a.ended_at, '+10 seconds')
 AND a.target_raw = b.target_raw
 AND a.id <> b.id
GROUP BY command_a, command_b
ORDER BY n DESC;
```

### Depth escalation

```sql
SELECT
    a.command,
    a.target_raw,
    a.max_depth AS old_depth,
    b.max_depth AS new_depth,
    COUNT(*) AS n
FROM cli_invocations a
JOIN cli_invocations b
  ON a.session_key = b.session_key
 AND a.command = b.command
 AND a.target_raw = b.target_raw
 AND b.started_at > a.started_at
 AND b.max_depth > a.max_depth
WHERE a.max_depth IS NOT NULL
  AND b.max_depth IS NOT NULL
GROUP BY a.command, a.target_raw, old_depth, new_depth
ORDER BY n DESC;
```

### Empty result 后的扩展查询

```sql
SELECT
    a.command AS empty_command,
    b.command AS followup_command,
    COUNT(*) AS n
FROM cli_invocations a
JOIN cli_invocations b
  ON a.session_key = b.session_key
 AND b.started_at > a.ended_at
WHERE a.empty_result = 1
GROUP BY empty_command, followup_command
ORDER BY n DESC;
```

## 后续实现建议

1. 先实现 SQLite 写入和 `cli_invocations` 主表。
2. 在 CLI 外层统一记录开始/结束时间、exit code、异常分类。
3. 在各子命令内部或统一 wrapper 中补充分阶段耗时。
4. 先写核心 columns 和四个 JSON 扩展列，不急于拆更多表。
5. 增加一个后处理命令或脚本，输出 session 指标、命令序列、retry、expansion、depth escalation。
6. 基于真实统计结果再决定新增组合命令、agent profile 输出或缓存/daemon 方案。
