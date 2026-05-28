# Roadmap

## 已完成

- Phase 1：CLI 工具化，核心查询能力可用。
- Phase 1.5：支持起点到目标字段的路径查询。
- Phase 1.6：增强字段诊断，支持 `_inherits` 委托链和可写性说明。

## 计划中

- Phase 1.7：为 agent CLI 调用增加本地 SQLite 埋点，统计 session 内多次查询、重试、参数升级与命令扩展模式。
- Phase 2：改进 override 判定（签名与 `super()` 检查）。
- Phase 3：补充方法体 AST 分析（compute/inverse 相关字段读写）。
- Phase 4：补充 XML view 字段引用解析。
- Phase 5：完善可视化与变更影响辅助能力。
