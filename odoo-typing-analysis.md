# Odoo 17 vs 19：Python 静态分析差异分析

## 背景

[odoo-ide/odoo-stubs](https://github.com/odoo-ide/odoo-stubs) 是一个为 Odoo 提供 Python 类型存根文件（`.pyi`）的第三方项目，用于让 IDE 和静态类型检查器（Pyright、Pylance、mypy 等）能理解 Odoo 的代码结构并提供自动补全、类型检查等功能。

该项目在 README 中声明：

> These stubs are no longer needed for Odoo >= 19. Please checkout other branches for Odoo <= 18.

## 核心结论

**Odoo 19 将类型注解（type annotations）直接内联到了核心源码中**，类型检查器可以直接从 `.py` 文件推断类型，外部 stub 文件变得多余。

## 详细对比

### Odoo 17.0 — 无类型注解

源码路径：`odoo/models.py`

```python
class odoo.models.Model(env, ids, prefetch_ids):
    _auto = False
    _table = None
    _name = None
    _description = None
    _abstract = True
    _transient = False
    _inherit = ()
    _inherits = {}
    _rec_name = None
    _order = 'id'
```

- 类构造函数参数**无类型标注**
- 类属性**无类型标注**
- 静态分析工具面对这些代码时是"盲"的
- 必须依赖外部 `odoo-stubs` 提供 `.pyi` 文件才能获得类型信息

### Odoo 19.0 — 内联完整类型注解

源码路径重组为：`odoo/orm/models.py`

```python
class odoo.models.Model(env: Environment, ids: tuple[IdType, ...], prefetch_ids: Reversible[IdType]):
    _auto: bool = True
    _table: str = ''
    _name: str = None
    _description: str | None = None
    _abstract: typing.Literal[False] = False
    _transient: bool = False
    _inherit: str | list[str] | tuple[str, ...] = ()
    _inherits: frozendict[str, str] = {}
    _rec_name: str | None = None
    _order: str = 'id'
```

- 构造函数参数有完整类型标注（`env: Environment`、`ids: tuple[IdType, ...]`）
- 类属性全部带类型（`_auto: bool`、`_table: str`）
- 使用了高级类型特性：
  - `typing.Literal[False]` — 精确字面量类型
  - `str | None` — PEP 604 联合类型语法
  - `frozendict[str, str]` — 泛型映射类型
  - `tuple[IdType, ...]` — 变长元组泛型
- 类型信息随代码一起演进，不会出现 stub 与实际代码不同步的问题

## 关键差异总结

| 维度 | Odoo 17 | Odoo 19 |
|---|---|---|
| 类型注解 | 无，纯运行时代码 | 内联完整类型标注 |
| Pyright/Pylance | 需要外部 stub 才能工作 | 直接从源码推断 |
| `odoo-stubs` | **必需** | **多余** |
| stub 维护成本 | 需要跟版本同步 | 无（类型随代码演进） |
| 类型准确性 | stub 可能与实际代码不同步 | 保证与运行时一致 |
| 源码结构 | `odoo/models.py` | `odoo/orm/models.py`（重组） |

## 原理解释

PEP 561 定义了 Python 包如何声明自己支持类型检查——通过在包内放置 `py.typed` marker 文件。当源码中包含内联类型注解时，类型检查器可以直接读取 `.py` 文件中的注解，不再需要任何外部 `.pyi` stub 文件。

`odoo-stubs` 本质上是为 Odoo 17/18 这种"源码里没有类型"的情况打的补丁。Odoo 19 把这个补丁的工作直接合并进了核心代码，因此第三方 stub 自然退役。

## 参考

- [odoo-ide/odoo-stubs](https://github.com/odoo-ide/odoo-stubs)
- [Odoo 17.0 ORM API](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html)
- [Odoo 19.0 ORM API](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- [PEP 561 – Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
