# 架构说明

## 总体流程

1. 通过 `odoo-bin shell` 启动 Odoo。
2. 运行 runtime probe，读取 `env.registry`。
3. 导出 `nodes.jsonl / edges.jsonl / edges_resolved.jsonl / summary.json / meta.json`。
4. 在本地加载为 NetworkX 图。
5. CLI 在图上执行查询。

## 关键设计

- 数据源是运行时 registry，而不是纯静态 AST。
- dump 与 query 分离：导出一次后可重复查询。
- 查询阶段不依赖数据库。

## 数据文件

默认目录：`~/.cache/odoo-graph/<db>/`

- `nodes.jsonl`：节点
- `edges.jsonl`：原始边
- `edges_resolved.jsonl`：解析后的字段依赖边
- `summary.json`：统计信息
- `meta.json`：环境信息

## 当前边界

- `dump` 依赖本机可启动 Odoo。
- 方法体内字段读写、XML 引用等复杂关系暂未覆盖。
