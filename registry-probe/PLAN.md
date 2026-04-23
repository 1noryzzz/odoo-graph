# Odoo 关系分析工具 — 阶段性规划

(参考 plan-eng-review / plan-devex-review skill 的节奏：Step 0 范围挑战 → 架构 → 代码质量 → 测试 → 开发者体验 → 下一步路线)

---

## Step 0 · 从 query_examples.txt 看到的真相

你跑的这次带了 34 个自定义 addon（`addons-oabay/`），和第一次 53 个纯官方 addon 的 dump 相比，信号变化很大 —— 这恰恰说明 runtime probe 方案真正**在你的业务环境里起作用了**。

### 真实业务场景里的关键信号

**1. 模型继承的广度，自定义 addon 已经压过官方：**

```
[6] res.partner  ['base', 'ifs_hr', 'mail', 'sms', 'website', 'website_partner']
[4] ifs.partner.merchant  ['ifs_gar_contract', 'ifs_gar_partner_relationship',
                           'ifs_gar_risk_manage', 'ifs_partner']
[3] sms.sms       ['galaxy_aliyun', 'galaxy_common', 'sms']
[3] ifs.partner.supplier
[3] ifs.partner.factor
```

`ifs.partner.*` 这套模型被 3-4 个 ifs_* 模块反复扩展 —— 这就是 PRD 第 0 段那张 Module A/B/C 继承图的**真实现场**。它之所以一直让开发者头大，因为 Odoo 官方没有任何工具能告诉你"这个 `merchant` 的某个字段到底被这 4 个模块里的谁动过"。

**2. Q4 override 链一下暴露出你的项目里最容易出问题的函数：**

```
depth=10  res.users.write    跨 10 个 addon (含 hr)
depth=9   res.users.create   跨 9 个 addon
depth=6   hr.employee.write  ['ifs_hr', 'hr_skills', 'hr', 'mail', 'mail']
depth=6   hr.employee.create ['ifs_hr', 'hr_skills', 'hr', 'mail', 'resource']
depth=5   res.users.authenticate  ['ifs_hr', 'wechat', 'website', 'auth_signup', 'base']
depth=5   ifs.work.position.write ['ifs_partner_hr', 'ifs_hr', 'mail', 'mail']
```

`res.users.authenticate` 跨 5 层、`hr.employee.write` 跨 6 层，这就是开发时最容易漏 super() 的点。这份清单单独就能做一份"代码审计清单"。

**3. Q5 字段冲突暴露了 _inherits 代理传播：**

这一堆 `ifs.gar.entry.supplier.*` 字段 `origin=None, modules=4` 是 probe bug（`_inherits` 代理字段 `_module` 被设为 None）。已经修掉了，`inherited=True` + `inherited_from_model` 都会标注清楚源头。新数据应该展示的是：**`ifs.gar.entry.supplier` 通过 `_inherits={'ifs.gar.invite.supplier': 'invite_id'}` 透传到祖先 `res.partner` 的整条链**。这是 PRD 里最有价值但最难静态看出来的关系。

### 三个从这次运行发现的已修 probe 问题

| 问题 | 现象 | 修复 |
|---|---|---|
| `related` 被 `list()` 成字符列表 | `['m','o','v','e','_','i','d',...]` | 改用 `.split('.')` |
| `_inherits` 代理字段丢失 `_module` | `ifs.gar.entry.supplier.vat origin=None` | 用 `field.inherited_field._module` 回填，新增 `inherited=True` 标注 |
| Q3 同一路径重复 | `avatar_1024` 对 `name` 依赖出现 2 次 | 单字段内去重；Odoo 把 MRO 里多个 compute 的 depends 拼接了 |

已 commit（`cedf0005`），已推。之所以先修而不是直接规划，因为规划是建立在"我们的数据能回答哪些问题"上的，数据污染了规划就错了。

---

## Step 1 · 你当前的两个 DX 痛点，直接对账

**痛点 A：手动启动服务 + 跑两次 py 文件**

现在的流程：
```
1. odoo-bin shell -d odoo_demo ... < dump_registry.py      # ~30s
2. python resolve_paths.py                                  # ~0.7s
3. python query_examples.py                                 # ~0.5s
```

这个确实麻烦。但是**"跑一次 dump"是硬成本**，因为 registry 只有在启动后才完整。可以消除的是：
- 两个 python 文件的割裂 → 合并为一次调用
- 每次都手敲 odoo-bin 一长串参数 → 一个命令
- 查询每次都要改代码 → 独立的 CLI / interactive 查询

**痛点 B：规划下一步要做什么**

PRD 的 3 大核心功能（6.2 节）：
1. 字段血缘分析 → **Demo 已能做，差一个顺手的命令行**
2. 影响分析 → **Demo 已能做，差一个顺手的命令行**
3. override 冲突检测 → **Demo 已能看到深度，差"同签名 vs 巧合同名"判定**

PRD 的非核心但有价值功能：
- 模型继承图可视化 → nodes/edges 已经够了，缺一个输出层
- XML 视图里的字段引用 → registry 没有，要 AST/XML 解析
- 方法体内的字段读写 → registry 没有，要 AST

---

## Step 2 · 架构决策 (Architecture)

### 保留的核心决策（和上一轮一致）

- Runtime probe 为主数据源（已验证）
- AST 只补 registry 拿不到的那部分（延后）
- 数据结构：图（NetworkX） + JSONL 持久化

### 新增的关键架构决策

**决策 A：把 probe + resolve + 查询 合并成一个 Python 包 `odoo_graph`**

```
odoo_graph/
├── __init__.py
├── dump.py          # 现 dump_registry.py 的代码，从 env 读 registry
├── resolve.py       # 把 depends 字符串路径解析成精确边
├── graph.py         # NetworkX 封装 (load from JSONL -> nx.MultiDiGraph)
├── queries.py       # field_lineage / impact_analysis / override_chain
├── cli.py           # argparse 入口
└── __main__.py      # python -m odoo_graph ...
```

这样用户只需要：

```bash
# 一次性 dump（内部自动做 resolve），放在 ~/.cache/odoo_graph/<db>/
python -m odoo_graph dump -d odoo_demo --db_host=127.0.0.1 -r odoo -w odoo

# 查询（不需要再启动 Odoo）
python -m odoo_graph field res.partner.name
python -m odoo_graph model ifs.partner.merchant
python -m odoo_graph module ifs_hr
python -m odoo_graph impact res.partner.name --max-depth=3
python -m odoo_graph overrides hr.employee.write
```

**决策 B：`dump` 命令封装掉 `odoo-bin shell` 的调用**

`dump.py` 既可以作为 subprocess 调用 `odoo-bin shell`，也可以作为 stdin 脚本被传入 shell。两种模式用同一份代码。优先子进程模式，这样用户不用记 `PYTHONPATH` 那套。

实现骨架：

```python
def cmd_dump(args):
    cmd = [sys.executable, f"{args.odoo_path}/odoo-bin", "shell",
           "-d", args.database, "--db_host", args.db_host, ...,
           "--no-http"]
    script = Path(__file__).with_name("_dump_runtime.py").read_text()
    subprocess.run(cmd, input=script, text=True,
                   env={**os.environ, "PYTHONPATH": args.odoo_path, ...})
```

**决策 C：查询层用 NetworkX，不是 Neo4j**

理由复述：Node ~100k / Edge ~30k，内存 <150MB，BFS/DFS 毫秒级。引入 Neo4j 增加一个"启一个数据库服务"的成本，完全不值得。真要 IDE 实时交互再升级。

**决策 D：method override 判定升级为 "同名 + 同签名 + super() 检查"**

当前脚本按 MRO 中同名 callable 即算 override，误报率肉眼大约 5% 左右（比如 `ir.http.session_info` 深度 10 的结果里，web / bus / mail 大概率是真实 override，但中间一两层可能只是 @classmethod 重定义）。升级方案：

1. 同名（现在就是）
2. 签名前两个参数一致（排除 classmethod vs instancemethod 这种）
3. 源码前 3 行做 `super().` 检查（可选，用 `inspect.getsource`）

这一步**不需要独立 AST 模块**，`inspect.getsource` 就够。标注 `calls_super=True/False/unknown`。

**决策 E：AST 层作为"可选增强"，不是硬需求**

AST 的价值点按优先级排：

| 功能 | 价值 | 难度 | P |
|---|---|---|---|
| 方法体 `self.<field>` 读写 | 高 | 中 | P1 |
| XML view 里 `<field name="...">` 引用 | 中 | 低 | P1 |
| `self.env['model'].xxx(...)` 跨模型调用 | 中 | 中 | P2 |
| `action.server.code` 里的 Python 片段 | 低 | 低 | P2 |

---

## Step 3 · 数据正确性 (Code Quality / Correctness)

修完上面 3 个 bug 后下一轮需要验证的点：

- [x] `related` 改为路径列表 ✅
- [x] `_inherits` 代理字段模块归属 ✅
- [x] `depends` 路径去重 ✅
- [ ] **MRO 里"只是 Python 基类不是 addon base"过滤是否充分** —— 当前按 `module.startswith('odoo.addons.')` 过滤，但 Q4 结果里 `addons=` 列表长度有时 < depth，说明还有一些 BaseModel 的同名方法被误计入 depth。需要把"非 addon 基类"也排除在 depth 统计之外。
- [ ] **abstract mixin depends 路径解析**（那 8 条 unresolved）—— 这是 Odoo 设计上的特性：mixin 只有被具体子模型继承后 `name` 才有定义。解决方案：对 abstract model 做 `inherit_children` 展开，把 mixin 的 depends 映射到每个具体子模型。
- [ ] **自定义 python 回调（`.compute = function_object`）被反射成方法 ID** —— 当前只取 `__name__`，但如果是 lambda 或装饰器包装，可能抓不到目标方法。打印 `__qualname__` 更稳。
- [ ] **跨 DB 一致性**：同一套代码在不同模块安装组合下 dump 出的结果要能 diff。nodes/edges 是 dict-based JSONL 已经支持，加一个 `meta.json` 记录 "db name / installed modules set / commit hash" 便于 diff。

---

## Step 4 · 测试与验证计划 (Test Review)

### 单元测试层

每个函数独立可测：
- `resolve_paths.py` 的路径展开 → 构造 fake registry JSONL，断言展开结果
- override 推断 → 构造 fake MRO，断言链条
- `_inherits` delegate 归属回填 → 构造 fake field 对象

### 集成测试层

保留一个最小 Odoo DB（比如只装 `base + mail`，初始化 5s），作为 smoke test：
- `python -m odoo_graph dump` 成功产出 nodes/edges
- `python -m odoo_graph field res.partner.name` 返回预期行数

### 回归断言（关键）

基于你这次 oabay 的运行结果，可以把这些变成 snapshot 断言：

```
res.partner 应该至少有 6 个模块扩展它（含 ifs_hr/website/wechat）
ifs.partner.merchant._inherits 链应该解析到 res.partner
hr.employee.write override depth >= 6
```

snapshot 文件放 `tests/fixtures/oabay_expected.json`，每次升级 probe 就跑一次对比。**你这次的 query_examples.txt 是绝佳的 snapshot 起点**。

---

## Step 5 · 开发者体验路线 (DX Review)

以下按 TTHW（Time To Hello World）降低量级排序：

**DX-1：把 dump 变成一个命令 —— 省 90% 的 DX 成本**

当前：需要记 `odoo-bin shell` + 参数 + stdin 重定向 + `PYTHONPATH` + `--addons-path`
目标：`odoo_graph dump -d <db>` 读 `~/.odoorc` 获取连接参数

**DX-2：查询输出结构化 —— 省大量手动 `jq`**

每个命令同时支持三种输出：
- `--format human`（默认，带颜色、ASCII tree）
- `--format json`
- `--format graphviz`（dot 语言，直接 `dot -Tsvg`）

**DX-3：增量 dump —— 开发迭代时 < 5s**

当前 dump 30s 是因为要启动整个 Odoo（加载 53 个模块）。但在本地开发时，如果只想看"我刚改了 `ifs_hr` 后依赖关系有没有变"，可以用一个已经启动的 Odoo 进程（开发服务）作为数据源，通过 XMLRPC / JSONRPC 调用 `ir.model.fields.search_read([])` + 一些自定义 endpoint。

**(增量 dump 是 P2 优化，P0 先不做)**

**DX-4：IDE 友好的输出路径**

dump 结果固定写到 `<workspace>/.odoo_graph/<db_name>/`，配合一个 VSCode 插件或者 `.gitignore` 约定，让开发者直接点开文件就能看图。

**DX-5：一个"受影响范围"打印器对接代码审查**

```bash
odoo_graph impact-for-diff HEAD~1 HEAD
# 输出：你这次改动涉及 res.partner.name / sale.order.amount_total，
#        可能影响 28 个下游 compute 字段 / 9 个 override 方法
```

这一步把工具从"查询"升级为"CR 助手"，是从开发工具变成团队工具的转折点。

---

## Step 6 · 完整的阶段分解 (按优先级)

### Phase 1 · 工具化（P0，下一步马上做）

**目标：用户只需要一条命令就能拿到当前运行 DB 的全景图并开始查询。**

- [ ] 新建 `odoo_graph/` Python 包结构
- [ ] `dump` CLI：子进程调用 `odoo-bin shell`，透传连接参数
- [ ] `resolve` 合进 `dump` 尾部（用户不需要再跑第二个脚本）
- [ ] `field/model/module/impact/overrides` 5 个查询命令
- [ ] 3 种输出格式（human/json/graphviz）
- [ ] 输出缓存 `~/.cache/odoo_graph/<db>/`
- [ ] 基础单元测试 + snapshot 测试（以本次 oabay 运行结果为基线）

**验收标准：**

```bash
pip install -e ./odoo_graph
odoo-graph dump -d odoo_demo
odoo-graph field res.partner.name
# 应能一次跑通，且输出稳定可对比
```

### Phase 2 · override 质量升级（P1）

- [ ] 排除非 addon 的 Python 基类后再计算 depth
- [ ] 用 `inspect.getsource` + 正则检测 `super().` 调用，标注 `calls_super`
- [ ] 同签名检查（`inspect.signature` 兼容性对比）
- [ ] 展示 `unknown`/`missing_super`/`has_super` 三态，**直接指出"可能漏 super 的 override"**

### Phase 3 · AST 补 compute/inverse 方法体里的字段读写（P1）

- [ ] 只对 `FIELD_COMPUTED_BY` / `FIELD_INVERSE_BY` 边目标方法跑 AST
- [ ] 记录 `self.<name>` 的 Name/Attribute 读写，生成 `METHOD_READS_FIELD` / `METHOD_WRITES_FIELD` 边
- [ ] `self.env['...'].xxx()` 跨模型读也记（匹配字符串字面量）

### Phase 4 · XML 视图引用（P2）

- [ ] 解析模块 data XML 里的 `<field name="x"/>` / `attrs` / `domain`
- [ ] 加 `VIEW_REFERENCES_FIELD` 边
- [ ] 可选：action server 里 Python 片段的 AST

### Phase 5 · 可视化与集成（P2）

- [ ] Graphviz 输出子图
- [ ] HTML 自描述报告（静态 site，可 commit 到 wiki）
- [ ] `impact-for-diff` 命令 —— 读 git diff 判断改动影响范围

---

## Step 7 · 不在本轮范围里 (NOT in scope)

写出来是因为会反复被问到，但**不要**现在做：

- ❌ Odoo 18/19 兼容：registry API 没变过，升级时再验证
- ❌ 图数据库（Neo4j/Memgraph）：NetworkX 够了，上数据库只是炫技
- ❌ VSCode 插件：先有 CLI 再说 IDE 集成，顺序反了就会无止境返工
- ❌ 运行时 hook 分析（monkey patch 追踪）：单独一个研究课题，不是工程问题
- ❌ 完整业务流追踪（action → controller → model）：XML 视图覆盖后再谈

---

## Step 8 · 下一步建议的落地顺序（从今天开始）

**立刻可以做的：**

1. 决定：Phase 1（工具化 CLI）是否作为下一个 PR 起点？  —— 推荐 ✅，价值最大、依赖最清晰
2. 决定：要不要在下一个 PR 里**先把 probe 基于 custom addons 的覆盖率做到 100%**（把那些 `origin=None` / `depth` 统计不匹配的细节都修掉）
3. 决定：demo DB 是否升级到装了 oabay 全套自定义 addon？ —— 这样 regression snapshot 会非常强，但初始化时间会从 30s 涨到 2-3min

**不确定的地方，需要你拍板：**

| 问题 | 选项 |
|---|---|
| CLI 命名 | `odoo-graph` / `ofields` / `odoo-deps` 选一个 |
| 打包形式 | pip 本地 editable / 独立 repo / 和 odoo 放一起 |
| 查询层第一版要不要 NetworkX | 是 / 否（直接 JSONL 扫也行，数据量不大） |
| 自定义 addon 是否纳入 CI snapshot | 是（推荐）/ 否 |
| 是否把 odoo-17.0 源码保留在仓库 | 目前 gitignore 了，建议改成 git submodule |

---

## 一句话总结

> **Phase 1（工具化 CLI + override 深度修正）是从"会跑的 demo"变成"能用的工具"的那一步**。PRD 里真正有价值的 3 大核心功能，都在 Phase 1 完成时就可以在开发日常里用上。Phase 2-4 是锦上添花，按需加。

---

## 附录：参考 plan-*-review skill 的哪些东西被吸收了

- **Step 0 先审查范围**（plan-eng-review §0）：不是 "我想做什么" 而是 "数据里看到的真相是什么"
- **完整性原则 Completeness / Boil the Lake**（多 skill 共用）：小范围内做完整实现，每个命令都 human / json / graphviz 三格式
- **NOT in scope 清单**（plan-eng-review 必产出）：明确拒绝清单防止范围蔓延
- **Failure modes 覆盖**（plan-eng-review §4）：列出了 probe 的 5 个已知边界 case
- **Parallelization 分析**（plan-eng-review "Worktree parallelization"）：Phase 1 / Phase 2 / Phase 3 之间互相独立，可以并行推进
- **DX Review 视角**（plan-devex-review）：把"启动服务 + 跑两次 py"识别为 TTHW 瓶颈
