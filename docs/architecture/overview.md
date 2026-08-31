# 架构说明

## 总体流程

1. 通过 `odoo-bin shell` 启动 Odoo。
2. 运行 runtime probe，读取 `env.registry`。
3. 导出 `nodes.jsonl / edges.jsonl / edges_resolved.jsonl / summary.json / meta.json`。
4. 在本地加载为 NetworkX 图。
5. CLI 在图上执行查询。
6. 业务查询命令默认写入本地 telemetry SQLite，供后续 session 分析。

## 关键设计

- 数据源是运行时 registry，而不是纯静态 AST。
- dump 与 query 分离：导出一次后可重复查询。
- 查询阶段不依赖数据库。
- telemetry 只记录本地 CLI 调用事实，不上传，不影响查询命令的 stdout 输出。

## 数据文件

默认目录：`~/.cache/odoo-graph/<db>/`

- `nodes.jsonl`：节点
- `edges.jsonl`：原始边
- `edges_resolved.jsonl`：解析后的字段依赖边
- `summary.json`：统计信息
- `meta.json`：环境与缓存来源信息（数据库、生成时间、Odoo 源码路径、
  生成时工作目录、工具版本、addons、summary 和 resolve 计数）

Telemetry 默认目录：`~/.cache/odoo-graph/telemetry.sqlite3`

- `cli_invocations`：业务子命令调用事实、耗时、目标、结果摘要、JSON 扩展信息

## 当前边界

- `dump` 依赖本机可启动 Odoo。
- `meta.json` provenance 仅供观察和人工核对，当前不会自动拒绝旧缓存。
- 方法体内字段读写、XML 引用等复杂关系暂未覆盖。
- telemetry 目前不统计 `--help`、`--version`、root action 或 shell 层启动失败。
