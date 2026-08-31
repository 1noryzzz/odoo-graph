# 使用说明

本文档说明 `odoo-graph` 的常用命令。

## 1. dump

用于导出 Odoo registry 数据。

```bash
odoo-graph dump -c odoo.conf -d odoo_demo
```

参数优先级：命令行参数 > `-c` 配置文件 > 默认值。

输出目录默认是：`~/.cache/odoo-graph/<db>/`。

Odoo 源码路径按以下优先级解析：

1. 显式 `--odoo-path`；
2. `ODOO_PATH`；
3. 从当前工作目录依次探测 `.`、`./odoo`、`./odoo-17.0`、
   `../odoo`、`../odoo-17.0`。

候选目录必须直接包含 `odoo-bin`。显式参数或环境变量指向无效目录时，
命令会报告已检查的候选和可复制的修正命令，不会自动回退。需要覆盖自动发现时可用：

```bash
odoo-graph dump -c odoo.conf -d odoo_demo --odoo-path /path/to/odoo
```

成功导出后，`meta.json` 会记录数据库、生成时间、Odoo 源码路径、生成时
工作目录、`odoo-graph` 版本和 registry 汇总计数。这些信息用于人工核对
缓存来源；1.9.1 不会自动拒绝旧缓存。

## 2. 查询命令

### 字段查询

```bash
odoo-graph field res.partner.name --db odoo_demo
```

用于查看字段上下游关系和字段诊断信息。

### 模型查询

```bash
odoo-graph model res.partner --db odoo_demo
```

用于查看模型继承关系、字段分布、委托链。

### 模块查询

```bash
odoo-graph module mail --db odoo_demo
```

用于查看模块定义和扩展内容。

### 上下文探索

```bash
odoo-graph context child.record --db odoo_demo
odoo-graph context child.record res.partner --db odoo_demo -f json
```

用于从一个 seed 模型发现下一步应查看的继承、委托和关系模型，或解释一组已知模型之间的运行时关系。单模型调用会输出 `suggested_context_models` 和可复制的 follow-up 命令；多模型调用会聚焦输入模型集合内部的关系。

显式模型组中的部分名称不存在时，命令仍返回有效模型，并通过
`result=partial`、`selected_models` 和 `missing_models` 明确区分结果。
缺失项附最多 3 个保守建议，部分成功退出码为 `0`；全部缺失时
`result=not_found` 且退出码非零。

### 影响分析

```bash
odoo-graph impact res.partner.name --db odoo_demo --max-depth 2
```

用于查看字段下游影响范围。

### 路径查询

```bash
odoo-graph path child.record res.partner.name --db odoo_demo
```

用于查看起点到目标字段的可达路径。

### override 链查询

```bash
odoo-graph overrides res.users.write --db odoo_demo
```

用于查看跨模块方法 override 链。

## 3. 输出格式

- `-f human`：文本输出
- `-f json`：JSON 输出

## 4. 本地 telemetry

业务子命令默认会记录到本地 SQLite，用于后续分析一次 task / session 内的多次 CLI 查询模式。

默认路径：

```text
~/.cache/odoo-graph/telemetry.sqlite3
```

显式初始化：

```bash
odoo-graph telemetry init
```

生成报告：

```bash
odoo-graph telemetry report
odoo-graph telemetry report --gap-seconds 60
odoo-graph telemetry report -f json
```

报告会包含：

- session 调用次数分布，以及 30s / 60s / 120s gap 敏感性分析
- 命令频率、follow-up、retry、参数升级
- `path` fan-out、批量 model / field 探索
- graph load overhead

配置与关闭：

```bash
ODOO_GRAPH_TELEMETRY_DB=/tmp/odoo-graph.sqlite3 odoo-graph telemetry report
odoo-graph field res.partner.name --db odoo_demo --no-telemetry
ODOO_GRAPH_TELEMETRY=0 odoo-graph model res.partner --db odoo_demo
```

`--help`、`--version`、root action 和 shell 层启动失败不会进入正式统计；telemetry 写入失败不会改变原命令的返回码。

## 5. 日志

日志写入 stderr，方便 stdout 作为机器可读输出。

```bash
odoo-graph -v field model.field --db odoo_demo
odoo-graph -q field model.field --db odoo_demo -f json
odoo-graph --log-level WARNING field model.field --db odoo_demo
```
