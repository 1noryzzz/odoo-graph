# `_inherits` 委托字段诊断改进记录

## 背景

一次排查中出现了误判：链式 `_inherits` 委托继承时，字段虽然不在子模型自己的 SQL 表里，但已经进入子模型 registry 的 `_fields`，并且可能因为 `inverse=_inverse_related` 可以通过子模型 `write()` 更新。只看 `information_schema.columns` 或源码静态字段声明会误判。

典型例子：

```text
ifs.gar.entry.supplier.vat
 -> ifs.gar.invite.supplier.vat
 -> ifs.base.company.vat
 -> res.company.vat
 -> res.partner.vat
```

## 已实现改进

`odoo-graph field <model.field>` 现在会在原有 upstream/downstream 外增加字段诊断：

- `kind`: 区分 `local / related / computed / delegated / delegated_related`
- `declared_on_model`: 是否当前模型直接声明
- `source_field`: 沿 depends/related 链追踪到的最终有效来源字段
- `writable` / `writable_reason`: 是否可通过 ORM 写入，以及原因
- `delegation_chain`: `_inherits` 的逐跳委托链，包含路径和 source
- `shadowing`: 同名字段覆盖/遮蔽风险

`odoo-graph model <model>` 现在会展开完整模型级 `Delegation chain`，用于确认链式 `_inherits` 结构。

## 用最新 dump cache 验证

验证 cache：

```bash
registry-probe/local_out
```

执行：

```bash
.venv/bin/python -B -m odoo_graph field ifs.gar.entry.supplier.vat --out-dir registry-probe/local_out -f human
```

关键输出：

```text
kind          : delegated_related
declared here : False
storage       : non-stored
source field  : res.partner.vat
writable      : True (writable: delegated_related field has inverse _inverse_related)
flags         : compute=_compute_related, related=invite_id.vat, inverse=_inverse_related

delegation chain:
  ifs.gar.entry.supplier.vat --invite_id (_inherits, path: invite_id.vat)--> ifs.gar.invite.supplier.vat
  ifs.gar.invite.supplier.vat --ifs_company_id (_inherits, path: ifs_company_id.vat)--> ifs.base.company.vat
  ifs.base.company.vat --company_id (_inherits, path: company_id.vat)--> res.company.vat

shadowing risk: watch - field is resolved through same-name delegated parent field(s)
```

结论：

- `ifs.gar.entry.supplier.vat` 不是当前模型直接声明的本地字段。
- 它是 `delegated_related`，当前模型 SQL 表里没有同名列并不代表 ORM 不可写。
- 最终有效来源字段是 `res.partner.vat`。
- 当前字段可写，原因是 delegated related 字段带 `inverse=_inverse_related`。
- 输出可以直接展示 `_inherits` 委托链和同名覆盖风险，避免后续分析再次只从 SQL 表结构误判。

## 测试

```bash
.venv/bin/python -m pytest odoo_graph/tests/ -q -p no:cacheprovider
```

结果：

```text
57 passed
```

## 原始分析记录

关于inverse=_inverse_related的计算字段：

  odoo-graph field ifs.gar.entry.merchant.need_fetch --db 17-oabay-ceshi

  输出要点：
  Field ifs.gar.entry.merchant.need_fetch [boolean]
  flags: related=invite_id.need_fetch, inverse=_inverse_related,
         inherited_from=ifs.gar.invite.merchant

  upstream:
  <- ifs.gar.invite.merchant.need_fetch (path: invite_id.need_fetch)

  再查上一层：

  odoo-graph field ifs.gar.invite.merchant.need_fetch --db 17-oabay-ceshi

  输出要点：

  Field ifs.gar.invite.merchant.need_fetch [boolean]
  origin-module: ifs_risk_manage
  flags: related=ifs_company_id.need_fetch, inverse=_inverse_related,
         inherited_from=ifs.base.company

  upstream:
  <- ifs.base.company.need_fetch (path: ifs_company_id.need_fetch)

  路径证明：

  odoo-graph path ifs.gar.entry.merchant.need_fetch ifs.base.company.need_fetch --db 17-oabay-ceshi

  输出：

  ifs.gar.entry.merchant.need_fetch
   -> ifs.gar.invite.merchant.need_fetch  via invite_id.need_fetch
   -> ifs.base.company.need_fetch         via ifs_company_id.need_fetch

  所以结论是：

  - need_fetch 不在 ifs_gar_entry_merchant SQL 表里，这个现象是真的。
  - 但它在 Odoo registry 的 ifs.gar.entry.merchant 模型上存在。
  - 它来自 _inherits 代理链：
    entry_merchant -> invite_merchant -> ifs_base_company
  - 因为字段带 inverse=_inverse_related，entry_merchant.write({'need_fetch': True}) 理论上是可以写的。

  odoo-graph 已经能证明这条链,但现在“能查到”和“很容易看懂”之间还有差距。：
  
    ifs.gar.entry.merchant.need_fetch
     -> ifs.gar.invite.merchant.need_fetch  via invite_id.need_fetch
     -> ifs.base.company.need_fetch         via ifs_company_id.need_fetch
  
    也能在 field 输出里显示：
  
    related=invite_id.need_fetch
    inherited_from=ifs.gar.invite.merchant
  
    以及上一层：
  
    related=ifs_company_id.need_fetch
    inherited_from=ifs.base.company
    origin-module=ifs_risk_manage
  
    所以底层图数据是够的。
  
    但我同意可以优化，因为这类 _inherits 委托继承很容易被误判。尤其是我前面就先从 SQL 表字段出发误判了一次。更好的输出应该直接告诉人：
  
    Field: ifs.gar.entry.merchant.need_fetch
    kind: delegated related field
    declared on current model: no
    physical storage: ifs_base_company.need_fetch
    storage table: ifs_base_company
    origin module: ifs_risk_manage
    writable through ORM: yes, via _inverse_related
    delegation chain:
      ifs.gar.entry.merchant.invite_id -> ifs.gar.invite.merchant
      ifs.gar.invite.merchant.ifs_company_id -> ifs.base.company
  
    我觉得可以从这几个方向优化：
  
    1. field 命令增加“最终源字段”
  
    现在 origin-module: None 对 ifs.gar.entry.merchant.need_fetch 有点误导。它应该额外显示：
  
    effective origin field: ifs.base.company.need_fetch
    effective origin module: ifs_risk_manage
  
    保留 origin-module: None 也可以，但要解释这是“当前代理字段没有直接源码定义”。
  
    2. 明确区分“物理字段”和“代理字段”
  
    比如：
  
    storage: delegated
    stored on: ifs.base.company.need_fetch
    current model column: no
  
    这样就不会再用 information_schema.columns where table_name='ifs_gar_entry_merchant' 得出错误结论。
  
    3. 对 _inherits 字段显示完整委托链
  
    model ifs.gar.entry.merchant 当前显示：
  
    _inherits: {'ifs.gar.invite.merchant': 'invite_id'}
  
    但如果父模型还有 _inherits，最好展开：
  
    Delegation chain:
      ifs.gar.entry.merchant --invite_id--> ifs.gar.invite.merchant
      ifs.gar.invite.merchant --ifs_company_id--> ifs.base.company
  
    4. 显示可写性原因
  
    对 related 字段很关键：
  
    writable: yes
    reason: inherited related field has inverse=_inverse_related
  
    如果是 readonly related，就显示：
  
    writable: no
    reason: readonly related field without inverse
  
    5. 显示同名字段覆盖风险
  
    如果当前模型自己定义了同名字段，_inherits 父字段不会代理上来。输出里可以标：
  
    shadowed delegated fields: ...
  
    或者在某个字段上显示：
  
    delegated parent field exists but is shadowed by local field
  
    结论：odoo-graph 现在已经能验证这种链式委托继承，但需要更偏“诊断视角”的展示。尤其是 field 输出应该直接回答三个问题：这个字段从哪里来、真实存在哪里、能不
    能通过当前模型写。
