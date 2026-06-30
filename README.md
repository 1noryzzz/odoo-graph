# odoo-graph

Odoo 模块、模型、字段、方法关系分析工具。

它通过 `odoo-bin shell` 读取 `env.registry`，导出 JSONL，再在本地构图查询。

## 这个工具解决什么问题

在多模块叠加后，开发中常见问题有：

- 某个字段改动后会触发哪些重算。
- 某个字段到底由哪个模块定义、哪些模块扩展。
- `_inherits` 委托字段的真实来源在哪里，能否通过当前模型写入。
- 某个方法的 override 链跨了哪些模块。

## 安装

```bash
git clone <repo>
cd odoo-relationship-analysis
uv venv
source .venv/bin/activate
uv pip install -e .
```

你还需要：

- Odoo 17 源码（例如本仓库中的 `odoo-17.0/`）
- PostgreSQL
- 已初始化的 Odoo 数据库

## 快速开始

### 1) 导出 registry

```bash
odoo-graph dump -c odoo.conf -d odoo_demo --odoo-path ./odoo-17.0
```

默认输出到：`~/.cache/odoo-graph/<db>/`

### 2) 本地查询

```bash
# 字段血缘（上游 + 下游）
odoo-graph field res.partner.name --db odoo_demo

# 模型全景（继承关系、字段分布、委托链）
odoo-graph model res.partner --db odoo_demo

# 模块归属（定义与扩展）
odoo-graph module mail --db odoo_demo

# seed-first 上下文探索（从一个模型发现继承/委托/关系候选）
odoo-graph context child.record --db odoo_demo

# 显式多模型上下文（解释一组已知模型间的关系）
odoo-graph context child.record res.partner --db odoo_demo

# 影响分析（下游范围）
odoo-graph impact res.partner.name --db odoo_demo --max-depth 2

# 路径查询（起点到目标字段）
odoo-graph path child.record res.partner.name --db odoo_demo

# override 链（跨模块方法覆盖）
odoo-graph overrides res.users.write --db odoo_demo
```

## 本地 telemetry

`odoo-graph` 默认会把业务子命令调用写入本地 SQLite，用于分析 agent 在一个 session 内是否反复查询、扩展查询或触发批量探索模式。

默认数据库路径：

```text
~/.cache/odoo-graph/telemetry.sqlite3
```

常用命令：

```bash
# 显式初始化 telemetry DB
odoo-graph telemetry init

# 生成后处理 + 分析报告
odoo-graph telemetry report

# 输出 JSON 报告，便于脚本处理
odoo-graph telemetry report -f json
```

可用 `ODOO_GRAPH_TELEMETRY_DB` 覆盖数据库路径。若某次调用不希望记录，可追加 `--no-telemetry`，或设置 `ODOO_GRAPH_TELEMETRY=0` 关闭。

## 输出格式

- `-f human`：默认文本输出
- `-f json`：结构化输出

## 文档导航

- 使用说明：`docs/guides/usage.md`
- 架构说明：`docs/architecture/overview.md`
- 产品与规划：`docs/product/roadmap.md`
- 变更记录：`docs/changes/README.md`

## 测试

```bash
uv pip install -e "[dev]"
uv run pytest
```
