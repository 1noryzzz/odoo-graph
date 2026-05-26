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
