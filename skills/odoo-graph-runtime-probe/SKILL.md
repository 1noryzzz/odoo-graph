---
name: odoo-graph-runtime-probe
description: 指导 AI 在 Odoo 开发中何时使用 odoo-graph 运行时探针工具，并正确选择命令（含 path 起点-终点查询）与解读输出。
---

# odoo-graph-runtime-probe

## 适用场景（何时应使用）
当用户的问题属于“运行时真实合并结果”而不是“源码静态猜测”时，优先使用 `odoo-graph`：

1. **字段影响分析**：修改某字段后会触发哪些 compute / depends 链。
2. **字段来源追踪**：字段由哪个模块定义、被哪些模块扩展。
3. **模型继承结构**：`_inherit / _inherits / mixin` 合并后实际结构。
4. **方法 override 链**：同名方法在多模块中的 MRO 顺序。
5. **起点到终点的路径证明**：想证明某业务对象是否能影响目标字段（`path` 命令）。

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
7. 输出优先 `-f human` 给人看；需要脚本处理时用 `-f json`。

---

## 命令清单：何时用、输入、输出

### 0) dump
```bash
odoo-graph dump -c odoo.conf -d <db> --odoo-path ./odoo-17.0
```
**何时用**：首次分析、数据库升级后、模块安装/升级后、或用户要求刷新缓存。  
**前置动作**：先确认目标 DB，再提醒潜在冲突并征求用户确认。  
**输出**：`~/.cache/odoo-graph/<db>/` 下的 `nodes.jsonl / edges.jsonl / edges_resolved.jsonl / summary.json / meta.json`。

### 1) field
```bash
odoo-graph field <model.field> --db <db>
```
**何时用**：看某字段上下游依赖。  
**输出**：该字段的 upstream/downstream 关系与统计。

### 2) model
```bash
odoo-graph model <model> --db <db>
```
**何时用**：看模型继承图、字段集合、按模块归属。  
**输出**：模型结构摘要与字段分组。

### 3) module
```bash
odoo-graph module <module_name> --db <db>
```
**何时用**：审计模块贡献（定义/扩展了什么）。  
**输出**：该模块涉及的模型、字段、方法等。

### 4) impact
```bash
odoo-graph impact <model.field> --db <db> --max-depth 2
```
**何时用**：改动评估、回归范围评估。  
**输出**：BFS 下游影响节点（按深度）。

### 5) path（重点）
```bash
odoo-graph path <start_node> <target_node> --db <db>
```
示例：
```bash
odoo-graph path child.record res.partner.name --db odoo_demo
```
**何时用**：需要“可达性证据链”时（从业务起点到目标字段）。  
**输出**：一条或多条从起点到终点的路径（节点序列 + 边关系）；不可达时明确无路径。

### 6) overrides
```bash
odoo-graph overrides <model.method> --db <db>
```
**何时用**：排查方法调用链、super 顺序争议。  
**输出**：跨模块 override 顺序（按 MRO 展示）。

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
5. **数据库参数规则**：
   - 若用户未提供 `--db` 且上下文无法唯一确定 DB，先询问再执行查询。
   - 优先给出缓存中可选 DB 列表，让用户选择。
   - 若用户提到的 DB 在缓存中存在，可直接分析并告知“正在使用缓存”。
   - 若用户不选缓存或要求最新数据，可提供“先 dump 新缓存再分析”的选项。
   - 不要擅自在多数据库环境下猜测 DB 名称。

## 推荐回答模板
1. 我会先列出缓存中可用 DB（若你未指定）。
2. 若你指定的 DB 在缓存中存在，我会直接用缓存分析。
3. 若你想要最新数据或缓存缺失，我会先提醒 dump 可能与运行中的 Odoo 冲突，并征求你确认。
4. 然后根据问题类型选择命令（field/model/module/impact/path/overrides）。
5. 给出简短结论，并附关键输出要点与下一步建议。

## 常见失败与处理
- `dump` 失败：优先检查 `-c`、`-d`、`--odoo-path`、DB 凭据。
- 查询报找不到 DB 缓存：先确认 DB 名称是否正确，再执行 `odoo-graph dump ...`。
- `path` 无路径：检查起点/终点标识是否准确，或链路被深度/解析能力限制。
