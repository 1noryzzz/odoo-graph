# 使用说明

本文档说明 `odoo-graph` 的常用命令。

## 1. dump

用于导出 Odoo registry 数据。

```bash
odoo-graph dump -c odoo.conf -d odoo_demo --odoo-path ./odoo-17.0
```

参数优先级：命令行参数 > `-c` 配置文件 > 默认值。

输出目录默认是：`~/.cache/odoo-graph/<db>/`。

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
- `-f graphviz`：预留

## 4. 日志

日志写入 stderr，方便 stdout 作为机器可读输出。

```bash
odoo-graph -v field model.field --db odoo_demo
odoo-graph -q field model.field --db odoo_demo -f json
odoo-graph --log-level WARNING field model.field --db odoo_demo
```
