# odoo-graph

> Odoo 模块 / 模型 / 字段 / 方法 依赖关系分析工具 — 通过 `env.registry` 运行时逆向导出。

解决的问题：Odoo 多模块叠加扩展后，开发时难以回答这类问题：

- `res.partner.name` 改一下，会触发哪些 compute 重算？
- `ifs.partner.merchant` 的某个字段，到底是哪个模块定义的、被哪些模块改过？
- `_inherits` 委托继承代理出来的字段，真实来源在哪里、能不能通过当前模型 `write()`？
- `res.users.write` 这个 override 链有多深？跨了哪些模块？

`odoo-graph` 通过 `odoo-bin shell` 启动 Odoo 后读 `env.registry`，把所有元数据 dump 成 JSONL，加载到 NetworkX 图里，然后提供 CLI 查询。

---

## 安装

```bash
git clone <repo>
cd odoo-relationship-analysis
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

你还需要：
- Odoo 17 源码（本仓库 `odoo-17.0/`）
- 一个 Postgres
- 一个已经初始化过的 Odoo 数据库（`odoo-bin -d mydb --init base --stop-after-init`）

---

## 快速开始

### 1) Dump 一次 registry（仅在需要刷新缓存时）

默认优先复用已有缓存 `~/.cache/odoo-graph/<db>/`；只有在首次分析、模块升级后或你明确需要刷新时再执行 dump。若本机已有正在运行的 Odoo 服务，建议先确认再 dump，避免潜在端口/进程冲突导致失败。

**推荐方式：复用你现成的 `odoo.conf`**

```bash
odoo-graph dump -c odoo.conf -d odoo_demo --odoo-path ./odoo-17.0
```

`odoo-graph` 会从 `[options]` 读 `db_host / db_port / db_user / db_password / addons_path`，并把 `-c` 透传给 `odoo-bin`，所以 `data_dir / log_level / unoconv` 等其他选项也会被 Odoo 自己读入。`-d` 在命令行给的话会覆盖 conf 里的 `db_name`；不给就用 conf 里的。

**无 conf 时的完整参数形式：**

```bash
PGPASSWORD=odoo odoo-graph dump \
  -d odoo_demo \
  --odoo-path ./odoo-17.0 \
  --addons-path ./odoo-17.0/addons-oabay \
  --db-user odoo --db-password odoo
```

**CLI 优先级规则：** `命令行参数 > -c conf > 默认值`。比如 `-c odoo.conf --db-host foo` 会用 `foo`，不用 conf 里的 `db_host`。

输出默认缓存到 `~/.cache/odoo-graph/<db>/`。包含 `nodes.jsonl` / `edges.jsonl` / `edges_resolved.jsonl` / `summary.json` / `meta.json`。

### 2) 查询（不再需要启动 Odoo）

若你本机有多个 DB 的缓存目录，可先查看 `~/.cache/odoo-graph/` 下的子目录并明确 `--db`，避免误用到其他库的 dump。

```bash
# 字段血缘（上游+下游）
odoo-graph field res.partner.name --db odoo_demo

# 字段诊断（来源、委托链、可写原因、同名覆盖风险）
odoo-graph field ifs.gar.entry.supplier.vat --db odoo_demo

# 模型全景（继承图 + 按模块分组的字段清单）
odoo-graph model res.partner --db odoo_demo

# 模块归属（定义了哪些模型/字段、扩展了哪些）
odoo-graph module mail --db odoo_demo

# 影响分析（BFS 下游，默认 depth=3）
odoo-graph impact res.partner.name --db odoo_demo --max-depth 2

# 路径寻路（从业务起点到目标字段）
odoo-graph path child.record res.partner.name --db odoo_demo

# Override 链（跨模块的方法 MRO）
odoo-graph overrides res.users.write --db odoo_demo
```

### 3) 输出格式

- `-f human`（默认，文本 tree）
- `-f json`（管道到 jq 等工具）
- `-f graphviz`（预留钩子，暂未实现；见 `odoo_graph/formatters.py`）

### 4) 日志

所有 log 都打到 **stderr**，stdout 保持干净（`-f json | jq` 不会被污染）。

```bash
odoo-graph field model.f --out-dir ...                 # 默认 INFO，告诉你查了啥、几条边
odoo-graph -v field model.f --out-dir ...              # DEBUG，看 graph 加载耗时、参数解析
odoo-graph -q field model.f --out-dir ... -f json      # 只打 ERROR，适合脚本里调用
odoo-graph --log-level WARNING field model.f ...       # 显式指定级别
ODOO_GRAPH_LOG=DEBUG odoo-graph field model.f ...      # 环境变量同效
```

**典型 INFO 输出（默认）：**

```
09:26:17 [INFO ] odoo_graph.graph: graph loaded: 149503 nodes / 67749 edges in 1.65s
09:26:17 [INFO ] odoo_graph.cli: field ifs.gar.partner.supplier.merchant.t18_contract_info_id: 0 upstream / 1 downstream
... 命令的实际输出 ...
```

**`-v` 时还会有：** `argv` 拆分、`out_dir` 解析路径、子命令参数、subprocess 命令行、Odoo stderr 尾部 60 行（dump 失败时排查必备）、未解析的 depends 路径前 10 条。

---

## 字段诊断：`_inherits` 委托继承

Odoo 的 `_inherits` 会把父模型字段代理到子模型上。这个字段可能出现在 `env['child.model']._fields` 里，也可以通过 `child.write({'field': value})` 更新，但它未必存在于子模型自己的 SQL 表中。`field` 查询会额外输出诊断信息，避免只看数据库表结构时误判。

```bash
odoo-graph field ifs.gar.entry.supplier.vat --db 17-oabay-ceshi
```

典型输出要点：

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

关键字段含义：

- `kind`: 字段形态。常见值包括 `local`、`related`、`computed`、`delegated`、`delegated_related`。
- `declared here`: 是否是当前模型直接声明的字段。`False` 时不要直接假设子模型 SQL 表有同名列。
- `source field`: 沿 depends/related 链追踪到的最终有效来源字段。
- `writable`: 是否可通过 ORM 写入，以及可写/不可写原因；例如 `inverse=_inverse_related` 会让 related 委托字段可写。
- `delegation chain`: `_inherits` 的逐跳委托链，包含当前模型、委托外键、父模型和路径。
- `shadowing risk`: 同名字段覆盖风险。若当前模型本地定义了同名字段，委托父字段可能被遮蔽；若当前字段来自委托链，则会列出同名父字段候选。

如果只想确认模型级委托结构，可以先跑：

```bash
odoo-graph model ifs.gar.entry.supplier --db 17-oabay-ceshi
```

`model` 输出会展开完整 `Delegation chain`，适合先确认 `_inherits` 是否是链式委托。

---

## 架构

```
┌─────────────────┐           ┌──────────────────┐            ┌───────────────────┐
│  odoo-bin shell │  (stdin)  │  _probe_script   │  (JSONL)   │   NetworkX graph  │
│  env.registry   │ ────────▶ │  dump.py driver  │ ─────────▶ │   graph.py        │
└─────────────────┘           │  resolve.py      │            │   queries + CLI   │
                              └──────────────────┘            └───────────────────┘
                                         │
                                         ▼
                          ~/.cache/odoo-graph/<db>/*.jsonl
```

- **Runtime probe** 是数据源。Odoo 在 `registry.setup_models()` 后已把 `_inherit` / `_inherits` / mixin 合并到位。
- **Dump** 一次 30s（大头是 Odoo 启动），产出的 JSONL 可以缓存复用。
- **Graph** 用 NetworkX MultiDiGraph（~100k 节点 / ~30k 边在 100MB 内存以内）。
- **查询** 全在本地 JSONL 上做，不再碰 DB；字段诊断会在图上追踪 related/depends 和 `_inherits` 委托链。

---

## 目录结构

```
odoo_graph/
├── __init__.py
├── __main__.py          python -m odoo_graph
├── _probe_script.py     runs INSIDE odoo-bin shell
├── dump.py              host-side subprocess driver + env wiring
├── resolve.py           depends string paths -> Field→Field edges
├── graph.py             NetworkX wrapper + query helpers
├── formatters.py        human / json / graphviz dispatch
├── cli.py               argparse entry
└── tests/
    ├── fixtures.py               synthetic graph for unit tests
    ├── test_resolve.py
    ├── test_graph.py
    ├── test_formatters.py
    ├── test_cli.py
    └── snapshot_asserts.py       CI post-dump assertions
```

---

## 运行测试

```bash
pip install -e ".[dev]"
pytest
```

CI 在每次 push / PR 上跑：

1. 单元测试（快，不需要 Odoo）
2. E2E smoke：装一个 minimal Odoo DB（`base + mail`）→ dump → 断言 summary 满足下限
3. 5 个 CLI 命令都跑一遍，JSON 输出正确

---

## 已知限制 (Phase 1)

- `dump` 需要 Odoo 能在本机启动（Postgres + 依赖包）
- `overrides` 的 depth 按"MRO 中同名 callable 即算一次"，不保证签名一致；Phase 2 会加 `inspect.signature` + `super()` 调用检查
- XML view 字段引用、方法体内的字段读写 — Phase 3/4 再加 AST 补

详见 [`registry-probe/PLAN.md`](registry-probe/PLAN.md)。

---

## Phase 路线

- ✅ **Phase 1** (本 PR) — CLI 工具化 + 5 个核心查询 + CI
- ✅ **Phase 1.5** (PR 7# 10#) — CLI 增加 path 参数，支持"起点-终点"的路径查询
- ✅ **Phase 1.6** — 字段诊断增强：区分 local/related/computed/delegated 字段，展示 `_inherits` 委托链、可写原因和同名覆盖风险
- ⏳ **Phase 2** — override 判定升级（同签名 + super 调用检查）
- ⏳ **Phase 3** — AST 补 compute/inverse 方法体的字段读写
- ⏳ **Phase 4** — XML view 字段引用解析
- ⏳ **Phase 5** — 可视化（graphviz 落地）+ `impact-for-diff` CR 助手
