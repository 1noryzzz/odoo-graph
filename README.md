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

# 影响分析（下游范围）
odoo-graph impact res.partner.name --db odoo_demo --max-depth 2

# 路径查询（起点到目标字段）
odoo-graph path child.record res.partner.name --db odoo_demo

# override 链（跨模块方法覆盖）
odoo-graph overrides res.users.write --db odoo_demo
```

## 输出格式

- `-f human`：默认文本输出
- `-f json`：结构化输出
- `-f graphviz`：预留，暂未实现

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
