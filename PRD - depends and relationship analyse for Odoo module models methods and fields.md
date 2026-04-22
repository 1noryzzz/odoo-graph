# Odoo 模块依赖与字段关系分析工具 PRD（初版 - discuss with GPT-5.3）

## 例子
有父模块A中的父模型a1有字段F0，然后存在2个新模块模型depends A，两个模块中各有一个模型b1和c1继承了a1并且添加了新的字段。
在这种情况下如果这个字段是计算字段或者 在b1或者c1中更新了F0，此时开发者会难以弄清楚这中间的依赖关系和逻辑（真实项目中的链条可能会更长且复杂）
Module A
|    |
|    - Model a1
|            |   - A new fields F0 to model A
|(depends A) |
|            |
Module B     |
|    |       |
|    - Model b1 (inherit a1)
|            |   - Add a new fields F1 to model B   
|            |   - Add a new logic to update F0 by F1
|(depends A) |
|            |
Module C     |
     |       |
     - Model c1 (inherit a1)
                 - Add a new fields F2 to model C, F2 maybe a compute field or a related field to model A

## 一、背景与问题定义

在 Odoo 开发中，模块、模型、方法、字段之间存在大量**跨模块、运行时组合的隐式依赖关系**。典型问题包括：

* 字段来源不清晰（多模块扩展 + 覆盖）
* 计算字段依赖链复杂（`compute` / `depends`）
* 方法 override 与 `super()` 调用链难以追踪
* 修改某字段后，难以评估影响范围
* 多模块对同一字段或方法的扩展存在潜在冲突

本质问题：

> Odoo 的依赖关系是“运行时组装”的，而不是静态显式定义，导致开发者难以建立完整的认知模型。

---

## 二、产品目标

构建一个：

> **Odoo 静态依赖分析与关系可视化工具**

核心能力：

1. 建立模块 / 模型 / 方法 / 字段之间的完整依赖关系图
2. 支持字段级别的血缘分析（lineage）
3. 提供变更影响分析（impact analysis）
4. 辅助定位 override 冲突与逻辑来源

---

## 三、核心设计原则

### 1. 图模型优先（Graph-based）

不采用“分层树结构”，而是统一为：

* **节点（Node）**

  * Module
  * Model
  * Field
  * Method

* **边（Edge）**

  * 所有关系均通过带类型的边表示

---

### 2. 静态分析为主（非运行时）

该工具是：

* 静态近似分析（best-effort）
* 不追求 100% 运行时还原
* 优先覆盖高价值依赖关系

---

### 3. 分阶段实现（避免过度复杂）

* 优先实现高确定性关系（P0）
* 延迟复杂动态分析（P2）

---

## 四、依赖图模型设计

### 4.1 节点类型

| 类型     | 描述      |
| ------ | ------- |
| Module | Odoo 模块 |
| Model  | ORM 模型  |
| Field  | 字段      |
| Method | 方法      |

---

### 4.2 边类型定义

#### 模块层

* `depends`: 模块依赖

---

#### 模型层

* `inherit_model`: `_inherit = 'a'`
* `inherit_mixin`: `_inherit = ['a', 'b']`
* `delegates_to`: `_inherits`

---

#### 定义关系

* `defines`: 模块 → 模型 / 字段 / 方法
* `overrides`: 方法 override
* `overrides_field`: 字段覆盖

---

#### 方法关系

* `calls_super`: super 调用链
* `calls_method`: 方法调用
* `cross_model_call`: 跨模型调用

---

#### 字段关系（核心）

* `computed_by`: 字段 → 方法
* `computes`: 方法 → 字段
* `depends_field`: 字段依赖字段
* `related`: related 字段链
* `inverse_by`: inverse 方法

---

#### 可选增强（后期）

* `reads`: 方法读取字段
* `writes`: 方法写入字段

---

## 五、分层能力拆解

### 5.1 模块层

**数据来源**

* manifest 中的 `depends`

**作用**

* 确定加载顺序
* 判断 override 生效顺序

**复杂度**

* 低

---

### 5.2 模型层

#### 支持类型

1. 单继承扩展（_inherit）
2. 多继承 / mixin
3. 委托继承（_inherits）

#### 关键点

* 多模块叠加扩展
* mixin 注入字段与方法
* delegation 带来的字段透传

#### 实现策略

* P0：支持 `_inherit` + mixin
* P1：支持 `_inherits`

---

### 5.3 方法层

#### 必须支持

* override 关系
* super 调用链

#### 扩展支持

* 方法调用关系（AST）
* compute / onchange 入口识别

#### 难点

* 间接调用（env、字符串调用）
* decorator 触发逻辑

---

### 5.4 字段层（核心复杂度）

#### 需要覆盖的关系

1. 字段定义与覆盖
2. compute
3. depends
4. related
5. inverse

#### 示例关系

* F1 depends F0
* F1 computed by `_compute_f1`
* F2 related to `partner_id.name`

#### 难点

* depends 路径解析（如 `x.y.z`）
* 跨模型字段追踪

---

## 六、功能设计（MVP）

### 6.1 查询能力

#### 按字段查询

输入：

```
model.field
```

输出：

* 定义链（来源模块）
* compute 来源
* depends 上游
* 被依赖下游

---

#### 按模型查询

输入：

```
model
```

输出：

* 继承关系图
* 字段来源分布（按模块）

---

#### 按模块查询

输入：

```
module
```

输出：

* 扩展了哪些模型
* 覆盖了哪些字段 / 方法

---

### 6.2 核心功能

#### 1. 字段血缘分析（最重要）

展示字段依赖链：

```
F0 → F1 → F2
```

---

#### 2. 影响分析

输入：

```
修改字段 F0
```

输出：

* 受影响字段（compute / related）
* 受影响模块
* 潜在影响方法

---

#### 3. override 冲突检测

输出：

```
字段 F0 被以下模块修改：
- module B
- module C
```

---

## 七、实现范围划分

### P0（必须）

* 模块依赖
* 模型继承
* 字段定义
* compute + depends

---

### P1

* 方法 override / super
* related 字段
* inverse

---

### P2

* 方法读写字段（AST）
* XML 视图依赖（attrs/domain）
* 动态行为分析

---

## 八、技术实现建议

### 8.1 数据结构

推荐：

* Python 内存结构（NetworkX）作为 MVP
* 后期可迁移到图数据库（如 Neo4j）

---

### 8.2 分析流程（Pipeline）

1. 扫描模块目录
2. 解析 manifest（模块依赖）
3. AST 解析 Python 文件
4. 提取：

   * 模型定义
   * 字段定义
   * 方法定义
   * decorator 信息
5. 构建依赖图
6. 提供查询接口

---

### 8.3 输出形式

* CLI 查询（MVP）
* JSON 结构（供 UI 使用）
* 图结构（后期可视化）

---

## 九、产品定位

该工具不是：

* IDE 插件（短期）
* 代码 lint 工具

而是：

> **面向 Odoo 的静态依赖分析与影响评估系统**

核心价值：

* 提升代码可理解性
* 降低维护成本
* 提供变更风险评估能力
* 支持复杂系统重构

---

## 十、总结

该工具解决的核心问题不是“代码查找”，而是：

> **让 Odoo 的隐式依赖关系变得显式、可查询、可分析**

在多模块、大规模项目中，其价值会随复杂度增长而显著提升。

下一步可进入：

* 数据结构设计细化
* AST 解析规则定义
* Prototype 实现
