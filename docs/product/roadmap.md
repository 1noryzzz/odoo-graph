# Roadmap

## 已完成

- Phase 1：CLI 工具化，核心查询能力可用。
- Phase 1.5：支持起点到目标字段的路径查询。
- Phase 1.6：增强字段诊断，支持 `_inherits` 委托链和可写性说明。
- Phase 1.7：增加本地 SQLite telemetry，支持业务命令实时采集与 `telemetry report` 后处理分析。
- Phase 1.8：新增 seed-first `context` 命令，压缩 agent 多模型探索流。

## 计划中

- Phase 2：MCP 入口与常驻进程/缓存方向评估，结合 telemetry 中的 graph load 成本，减少 agent 连续查询时的重复加载。
- Phase 2.x：改进 override 判定（签名与 `super()` 检查）。
- Phase 3：补充方法体 AST 分析（compute/inverse 相关字段读写）。
- Phase 4：补充 XML view 字段引用解析。
- Phase 5：完善可视化与变更影响辅助能力。
