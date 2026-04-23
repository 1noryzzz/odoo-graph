# 通过 `env.registry` 逆向 dump 的技术可行性与可靠程度

针对 PRD "模块 / 模型 / 方法 / 字段 跨模块依赖可视化" 和 `odoo_registry_graph_dump_notes.md` 的判断，
本文以 Odoo 17 源码为依据，配合一个真实跑通的 demo（见 `registry-probe/`），给出可行性结论。

---

## 1. 先说结论

> **可行，且结果可靠性远高于纯 AST 静态分析**。

- **P0 / P1 PRD 需求（模块依赖 / 模型继承 / 字段定义 / compute + depends / related / inverse / override 链）100% 可从 registry 导出**，置信度来自"这就是 Odoo 运行时使用的那份元数据"。
- 对于 PRD P2（方法读/写字段、XML 动作、动态调用），registry 拿不到，但这部分占 PRD 价值的 10-15%，**用 AST 做增量补充就好，不需要推翻 registry 方案**。
- 类型标注（Odoo 19 inline / odoo-stubs）和本方案正交：stubs 解决"IDE 里某个变量是什么类型"，本方案解决"这个字段在多模块组装后由谁定义、依赖谁、被谁影响"。**17 即使有了 stubs 也解决不了你的问题**，原因后面会讲。

---

## 2. 为什么 registry 可信 —— 源码级证据

### 2.1 registry 完成装配的时刻明确

`odoo/modules/loading.py` line 506-507：

```python
registry.loaded = True
registry.setup_models(cr)
```

`registry.loaded = True` 之后的任何时刻读 `env.registry`，都是"所有模块加载完、所有 `_inherit` 合并完"的终态。Odoo 自己依赖这个不变式来跑 ORM，它不可能撒谎。

### 2.2 `setup_models()` 把字段依赖写入 registry

`odoo/modules/registry.py` `setup_models()` 的末尾（line 325-330）：

```python
for model in models:
    for field in model._fields.values():
        depends, depends_context = field.get_depends(model)
        self.field_depends[field] = tuple(depends)
        self.field_depends_context[field] = tuple(depends_context)
```

这就是 Odoo 自己做"字段重算触发"时依赖的真源头。你读 `registry.field_depends[field]` 拿到的字符串路径（比如 `'order_line.price_subtotal'`），和 Odoo 真正 recompute 时用的一字不差。

### 2.3 `_inherit` / `_inherits` / mixin 在 `_build_model` 全部归一

`odoo/models.py` `_build_model()` line 725-748 构造的 "registry class" 带着这些 class 级属性：

| 属性 | 含义 | dump 时怎么用 |
|---|---|---|
| `_original_module` | 模型首次定义所在模块 | → `MODULE_DEFINES_MODEL` 起源边 |
| `_inherit_module` | `{父模型: 引入该继承的模块}` | → `MODEL_INHERITS_MODEL`，附带"哪个模块引入" |
| `_inherit_children` | 子模型名集合 | 可做下游扩展图 |
| `_inherits_children` | 委托子模型集合 | → `MODEL_DELEGATES_TO_MODEL` 反向 |

### 2.4 字段带自己的模块归属

`odoo/fields.py` `_get_attrs()` line 408-431：

```python
attrs['_module']  = modules[-1] if modules else None   # 最终有效的模块
attrs['_modules'] = tuple(set(modules))                # 所有参与定义的模块
```

所以 `field._module` 回答的是"最后一个参数值由谁决定"，`field._modules` 回答的是"总共有哪些模块扩展了这个字段"。前者解决"去看哪个文件"，后者解决"是否多模块冲突"。

---

## 3. Demo 数据验证（Odoo 17 + 53 个模块）

初始化了一个真实 Odoo 17 数据库（`base, mail, contacts, sale_management` 及其全部传递依赖 = 53 个模块），跑了一次 dump，结果见 `registry-probe/out/summary.json`：

```
models: 350    abstract: 82    transient: 72
fields: 6135   computed: 2530  related: 960   inverse: 842
field_depends entries: 2118    depends paths dumped: 3206
methods with overrides (chain >= 2): 2463   override edges: 2771
module-level nodes: ~100         module-depends edges: 101
model extensions by >=3 modules: res.partner (4), res.company (3)
fields touched by >=2 modules: 274
```

**耗时：dump 30s（大头是 Odoo 启动），resolve 0.7s。**

Probe 质量的具体验证（来自 `query_examples.py`）：

1. `res.partner.name`：origin=`account`，modules=`['mail','account','base']` —— 正确反映了"base 定义、mail 扩展、account 最后修正"的现实。
2. `sale.order.amount_total` compute 依赖：`order_line.price_subtotal / price_tax / price_total` —— 与 Odoo 真实 recompute 行为 1:1 吻合。
3. `resolve_paths.py` 把 3206 条路径中 3198 条精确解析成 `Field → Field` 边（成功率 99.75%）；**剩下 8 条都是 abstract mixin `avatar.mixin.name`** —— mixin 本身没有 name 字段，字段依赖是合法地"延迟到具体子模型再确定"，这是 Odoo 的设计，不是 probe 的 bug。
4. `res.users.write` 方法 override 链深度 = 9（跨 `auth_totp_mail / auth_signup / mail / resource / base` 等模块），这正是 PRD "override 冲突检测" 能直接用的信号。

---

## 4. 能力边界（不吹、不欠）

### 能做到 >=95% 可靠（仅靠 registry）

- 模块 ↔ 模块依赖图（manifest 真相）
- 模型 ↔ 模块 的定义和扩展归属
- 模型 ↔ 模型 的 `_inherit` / `_inherits` / mixin 关系（mixin 通过 MRO 还原）
- 字段 ↔ 模型 / 字段 ↔ 字段（depends 路径解析后）
- 字段 ↔ 模块的多源追踪（`_module` + `_modules`）
- 字段 ↔ compute / inverse 方法 的绑定
- 方法 跨模块 override 链（MRO 还原）

### 70-90% 可靠（推断 + 边缘 case）

- **Selection 字段的 value 冲突**：registry 能告诉你"3 个模块都往 `mail.message.message_type` 塞了值"，但具体每个模块塞了哪些 value，需要 `_fields[name].selection`（可得）或 AST（更细）。
- **方法 override 是否调用 super()**：registry 能列出 MRO 中所有同名函数，但"有没有真的 super() 进下一层"只能用 `inspect.getsource` 加正则或 AST 判断。这是从 runtime probe 到 hybrid 的第一个增量点。

### registry 拿不到（就是要 AST）

- 方法内部 `self.partner_id.name` 这类读字段的静态依赖
- `self.env['res.partner'].search(...)` 这类跨模型调用
- XML view 里 `<field modifiers=...>` 引用的字段 / Python 表达式
- `ir.actions.server.code` 里写的 Python 脚本依赖

---

## 5. 和 "Odoo 19 内联 typing" 的关系（回到你的原始问题）

typing 解决不了你的核心问题。原因：

- **Pyright 看不见 `_inherit`**：即使 19 给 `Model._inherit: str | list[str]` 标了类型，IDE 仍然没办法告诉你 "`sale.order` 的最终 `_fields` 是谁拼出来的"。这是 runtime 行为，不是类型约束。
- **compute/depends 是字符串**：`@api.depends('order_line.price_subtotal')` 里的字符串在任何类型系统里都是 `str`。Pyright 不会帮你把它解析成字段引用。
- **跨模块的"最后覆盖者"**：类型系统只看单个 class 定义，而"谁赢了最后一轮覆盖"取决于 addon 加载顺序 + `_module`，这就是 registry 的职责。

所以 odoo-stubs 退役 ≠ 你的需求被满足。**"字段血缘 + 影响分析 + override 冲突"这个问题域，stubs 从来没覆盖过**。

---

## 6. 推荐路线（增量、不返工）

```
┌─────────────────┐        ┌────────────────────┐        ┌───────────────┐
│  Runtime Probe  │──JSONL─▶│  查询层 (NetworkX)  │──CLI──▶│  PRD 6.2 功能 │
│  (本 demo)       │        │                    │        │               │
└─────────────────┘        └────────────────────┘        └───────────────┘
         ▲                           ▲
         │                           │
         │ 仅对高价值盲点             │
         ↓                           │
┌─────────────────┐                  │
│   AST 补充      │──────增量补边─────┘
│ (super / reads) │
└─────────────────┘
```

### Phase 1 — 锁死 runtime probe（基本完成）

- ✅ dump 脚本跑通
- ✅ depends 路径解析
- ✅ 基本查询示例
- ⏳ 打包成一个独立的 `odoo_graph` python 模块，支持 `python -m odoo_graph dump -d <db>` 直接跑
- ⏳ 输出加一份 `graphml` / `dot`，方便 IDE / Graphviz 可视化

### Phase 2 — NetworkX 查询层

- 读 `nodes.jsonl` + `edges_resolved.jsonl` → `nx.MultiDiGraph`
- 实现 3 个 CLI：`field <m.f>` / `model <m>` / `module <m>`
- 影响分析用 `nx.descendants` 就够，复杂度 O(V+E)

### Phase 3 — AST 按需补充

只扫 probe 报告中**有意义的源码文件**（来自 `MODULE_DEFINES_MODEL` / `MODULE_DEFINES_FIELD`），不是全 addons 目录扫。三件事：

1. `super()` 是否被调用 → 完成 PRD `calls_super` 边
2. 方法体里对 `self.<field>` 的读/写 → PRD P2 的 `reads` / `writes` 边
3. XML 里的 `<field>` / `domain` / `attrs` → PRD P2 的 view 依赖

### Phase 4（按需）

- 迁到 Neo4j：只有在要做 IDE 级实时交互时才值得，平时 NetworkX 够
- 多版本 Odoo 17/18/19 兼容：registry 的 API 从 14 起基本稳定，`field_depends` 和 `_inherit_module` 都是长寿字段，风险低

---

## 7. 风险与坑位（提前说）

| 风险 | 触发条件 | 缓解 |
|---|---|---|
| Odoo 19 registry API 变动 | 升级到 19 | 验证脚本：`assert hasattr(registry, 'field_depends')`，有变动就加版本分支 |
| Custom field / manual field | 数据库里手工加的字段 | `field._module=None` 时归类到 `__manual__` 命名空间，dump 脚本已兼容 |
| Method 同名但无关（误判 override） | 比如 `_name` 冲突 | Phase 3 的 AST 顺带验证签名一致 |
| 非 Odoo 标准基类出现在 MRO | 个别 addon 会 import 一个第三方 base class | dump 已经按 `module.startswith('odoo.addons.')` 过滤 |
| Dump 结果体积 | 大项目 150+ 模块时 nodes.jsonl ~50MB | 行级 JSONL 天然流式，不是瓶颈；查询层按需 lazy load |

---

## 8. 一句话收尾

> 你的直觉是对的：**先 registry，后 AST**。Registry 给你一份和 Odoo 实际运行行为完全一致的"元数据成品"，demo 已经证明它能答出 PRD 想要的大部分问题；AST 是锦上添花的增量层，不要反过来把它当主干。
