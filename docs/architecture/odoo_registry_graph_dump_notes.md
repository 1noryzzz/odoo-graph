# Odoo 启动后 Registry 图模型可导出性说明

## 目标问题

确认以下判断是否成立，并给出可落地的导出边界：

- Odoo 启动后，`_inherit`、`_inherits`、mixin、override 是否都已合并
- 合并结果是否可从 `env.registry` 与 `Model._fields` 读取
- 是否可通过启动脚本一次性导出“模块/模型/字段/函数”的依赖与继承图（节点+边）


## 核心源码依据

### 1) 模块加载结束后统一执行模型 setup

`odoo/modules/loading.py` 在 registry 完成模块加载后，调用 `registry.setup_models(cr)`：

- `registry.loaded = True`
- `registry.setup_models(cr)`

这意味着读取 registry 时机应放在该步骤之后。

### 2) setup_models 内部完成模型与字段元信息归并

`odoo/modules/registry.py` 的 `setup_models()` 关键顺序：

1. 遍历模型执行 `_setup_base()`
2. 遍历模型执行 `_setup_fields()`
3. 遍历模型执行 `_setup_complete()`
4. 为每个字段计算并缓存 `field_depends / field_depends_context`

因此，字段依赖关系可直接来自：

- `registry.field_depends`
- `registry.field_depends_context`
- `Model._fields`

### 3) _inherit / _inherits 在 build/setup 阶段合并

`odoo/models.py` 的 `_build_model()` 和 `_setup_base()` 体现了两层合并：

- `_build_model()`：构建 registry class，合并父类与继承链，维护
  - `_inherit_module`
  - `_inherit_children`
  - `_inherits_children`
- `_setup_base()`：
  - 先归并当前模型字段定义
  - 再执行 `_inherits_check()` 与 `_add_inherited_fields()`
  - 最终得到可直接消费的 `cls._fields`

因此 `_inherits` 委托字段在 setup 后会进入子模型可见字段集合中。


## 结论（可用于实现）

## 可直接导出的关系（高置信）

通过启动后脚本读取 `env.registry` / `Model._fields`，可以稳定导出：

- 模型节点（`model_name`）
- 字段节点（`model_name.field_name`）
- `MODEL_INHERITS_MODEL`（来自 `_inherit` 语义）
- `MODEL_DELEGATES_TO_MODEL`（来自 `_inherits`）
- `MODEL_HAS_FIELD`
- `FIELD_RELATES_TO_MODEL`（`many2one/one2many/many2many` 的 comodel）
- `FIELD_DEPENDS_ON_FIELD`（来自 `registry.field_depends`）
- 模块归属信息（模型 `_module`、字段 `_module/_modules`）

## 可推断但需约定算法的关系（中置信）

- mixin 关系：本质属于继承链的一部分，可通过 model class 的 MRO / base classes 推断
- override 关系：可通过 MRO + `inspect` 比较方法定义位置，构建 `METHOD_OVERRIDES_METHOD` 边

说明：这部分不是 Odoo 直接给出的“现成边”，需要在导出脚本中定义推断规则。

## 不能仅靠 registry 静态快照完整得到的关系（低置信或不可得）

- 完整运行时函数调用图（动态分支、条件调用、外部服务调用）
- UI/XML Action 到 Python 方法的全链路触发图
- monkey patch/运行期注入对调用路径的影响


## 建议图模型（节点/边）

节点类型：

- `Module`
- `Model`
- `Field`
- `Method`

边类型：

- `MODULE_DEPENDS_ON_MODULE`
- `MODULE_DEFINES_MODEL`
- `MODEL_INHERITS_MODEL`
- `MODEL_DELEGATES_TO_MODEL`
- `MODEL_HAS_FIELD`
- `FIELD_RELATES_TO_MODEL`
- `FIELD_DEPENDS_ON_FIELD`
- `METHOD_OVERRIDES_METHOD`（推断）


## 启动脚本最小导出清单

建议脚本在 Odoo 环境初始化并拿到 `env` 后执行，最小读取项：

- `env.registry.models`
- `Model._name / _module / _inherit / _inherits / _fields`
- `field.type / field.comodel_name / field._module / field._modules`
- `env.registry.field_depends`
- `env.registry.field_depends_context`

输出格式建议优先 JSONL（节点文件 + 边文件），后续可转换到 Neo4j / Graphviz / NetworkX。


## 一句话结论

“启动后 dump registry”是构建 Odoo 模型/字段继承依赖图的正确入口，能够覆盖大部分 ORM 元数据关系；但若目标是完整业务调用图，还需叠加方法级静态分析与运行期观测。
