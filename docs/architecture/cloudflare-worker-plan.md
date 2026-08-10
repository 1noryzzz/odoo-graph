# Cloudflare Worker 演进计划

## 1. 目标

将 odoo-graph 从仅在本机运行的 Python CLI，逐步演进为：

1. 可公开访问的项目与安装信息站点。
2. 可由 AI Agent 发现和理解的安装、使用入口。
3. 团队共享的 Odoo registry 图快照与查询服务。
4. 可供 Codex、Cursor、Claude 等客户端连接的远程 MCP Server。
5. 具备统一 telemetry、版本对比和 CI 影响分析能力的平台。

这不是把整个 CLI 原样部署到 Worker。现有 dump 与 query 的分离设计应继续保留。

## 2. 当前架构与边界

当前流程：

1. 通过 odoo-bin shell 启动 Odoo。
2. runtime probe 读取 env.registry。
3. 导出 nodes.jsonl、edges.jsonl、edges_resolved.jsonl、summary.json 和 meta.json。
4. 本地加载为 NetworkX 图。
5. CLI 执行 field、model、module、context、impact、path、overrides 等查询。
6. 本地 SQLite 记录 telemetry。

关键边界：

- dump 依赖完整 Odoo 源码、addons、PostgreSQL、配置文件和子进程。
- query 阶段不再依赖 Odoo 或业务数据库。
- Cloudflare Workers 不适合执行 odoo-bin shell，也不应直接连接生产 Odoo 并加载 registry。
- Worker 的职责应从已生成的快照开始。

## 3. 目标架构

~~~mermaid
flowchart LR
    A["本地 / CI / Odoo Pod<br/>生成 registry dump"] --> B["R2<br/>不可变快照"]
    B --> C["Worker<br/>HTTP API / MCP"]
    C --> D["Codex / Cursor / Claude"]
    C --> E["D1<br/>索引与 telemetry"]
~~~

组件职责：

| 组件 | 职责 |
| --- | --- |
| Python CLI | 生成 dump、校验、打包和上传快照 |
| R2 | 保存原始、不可变、可恢复的快照文件 |
| D1 | 保存节点/边查询索引、版本元数据和 telemetry |
| Worker | 静态站点、查询 API、MCP、鉴权和限流 |
| GitHub Actions 或自托管 Runner | 构建、测试、部署和快照差异分析 |
| Cloudflare Access / OAuth | 控制私有项目和 MCP 工具的访问权限 |

建议的快照标识：

~~~text
<project>/<environment>/<revision>/
~~~

例如：

~~~text
oabay/dev/abc123/
oabay/prod/def456/
~~~

## 4. 第一阶段：项目介绍与 Agent 发现入口

第一阶段先把 Worker 当作一个带固定 URL 的轻量项目站点，不引入 D1、R2 或 MCP。

建议公开以下路径：

| 路径 | 面向对象 | 内容 |
| --- | --- | --- |
| / | 人类用户 | 项目介绍、能力、安装和文档导航 |
| /install | 人类用户 | 安装、升级、卸载和验证说明 |
| /install.md | AI Agent | 精简且可直接读取的安装与验证步骤 |
| /llms.txt | AI Agent | 项目摘要和权威文档入口索引 |
| /manifest.json | 工具 | 版本、Python 要求、安装源、命令和文档 URL |
| /health | 部署检查 | 服务版本和构建 revision |
| /mcp | 后续 MCP | 第一阶段不启用或返回明确的未开放状态 |

### 4.1 llms.txt 的定位

llms.txt 是面向 LLM 的发现约定，目前仍是提案，不是“自动安装协议”。

它应告诉 Agent：

- odoo-graph 是什么。
- 适合在什么任务中使用。
- 权威安装说明在哪里。
- CLI/MCP 文档在哪里。
- 安全边界和前置条件是什么。

真正的安装步骤放在 install.md，并同时提供结构化 manifest.json。

### 4.2 建议的安装方式

odoo-graph 是命令行工具，优先采用隔离安装：

~~~bash
uv tool install odoo-graph==<version>
~~~

如果尚未发布到 PyPI，使用固定 release tag 或 commit SHA，而不是默认跟随 main：

~~~bash
uv tool install "git+https://github.com/1noryzzz/odoo-graph.git@<tag-or-sha>"
~~~

兼容入口：

~~~bash
pipx install "git+https://github.com/1noryzzz/odoo-graph.git@<tag-or-sha>"
~~~

安装文档必须同时提供：

- Python 版本要求。
- uv 或 pipx 前置条件。
- 安装、升级和卸载命令。
- odoo-graph --version 验证命令。
- dump 所需的 Odoo、addons 和 PostgreSQL 前置条件。
- 查询阶段与 dump 阶段的权限区别。
- 失败时停止并向用户报告的规则。

Agent 不应仅因访问到网页就自动执行安装。网页提供可验证的说明，是否执行仍应受 Agent 客户端权限和用户确认规则约束。

## 5. GitHub Pages、Cloudflare Pages 与 Workers

### 5.1 GitHub Pages

适合：

- 纯静态项目介绍和文档。
- 与仓库 Markdown/Jekyll 紧密同步。
- 不需要 API、鉴权、MCP 或动态路由。

不足：

- 只能作为静态站点。
- 未来增加 /api、/mcp、D1、R2 和 Access 时需要迁移或增加第二个域名。
- github.io 及 GitHub 相关资源在中国大陆的可访问性和延迟无法保证。

### 5.2 Cloudflare Pages

也适合纯静态站点，但本项目的长期目标是 Worker API 和远程 MCP。单独选择 Pages 会产生一次可避免的迁移。

### 5.3 Workers Static Assets

推荐作为主入口。

理由：

- 第一阶段可以只托管静态资源。
- 静态资源与 Worker 代码可以一次部署。
- 后续可在同一域名下增加 /api、/mcp、鉴权、D1 和 R2。
- 不需要为了动态能力迁移站点或改变 Agent 配置中的权威 URL。

推荐策略：

- GitHub 仓库仍是源代码和文档的权威来源。
- Worker 自定义域名是面向人类和 Agent 的稳定入口。
- GitHub Pages 可选做只读镜像，但不是必需项。

## 6. 中国大陆可访问性

需要区分“使用 Cloudflare 全球网络”与“接入 Cloudflare 中国网络”。

普通免费/付费 Workers 和自定义域名运行在 Cloudflare 全球网络，并不等于获得中国大陆境内节点。跨境访问仍可能出现较高延迟、偶发失败或不同运营商表现不一致。workers.dev 共享域名也不适合作为长期权威地址。

第一阶段建议：

1. 使用自有域名，例如 odoo-graph.example.com，不把 workers.dev 写入永久配置。
2. 页面保持纯静态、体积小、无第三方字体和外部 JavaScript。
3. install.md、llms.txt 和 manifest.json 全部从同一域名直接返回。
4. GitHub URL 作为源码回退入口，但不要让页面渲染依赖 GitHub。
5. 从电信、联通、移动网络分别做实际连通性测试。
6. 如果主要是个人和小团队使用，先接受“尽量可访问但不保证”的级别。

如果需要面向中国大陆用户提供正式 SLA，应考虑：

- ICP 备案。
- 中国大陆云厂商或境内镜像。
- Cloudflare Enterprise + China Network 单独订阅。
- 必要时为动态 API 使用 Global Acceleration。

Cloudflare China Network 不是普通 Workers 套餐自动包含的能力。

## 7. 第二阶段：快照发布

为 Python CLI 增加 publish 能力：

1. 校验 dump 完整性。
2. 生成 manifest 和内容哈希。
3. 移除或脱敏本机绝对路径、数据库凭据和不应上传的环境元数据。
4. 上传到 R2。
5. 注册 project、environment、revision、created_at 和 schema_version。
6. 保留 latest 指针，但查询请求应允许固定 revision。

不允许 Worker 主动连接生产 Odoo 执行 dump。

## 8. 第三阶段：图查询 API

不要在每次请求中下载整个 dump 并重建 NetworkX 图。

建议将节点和边导入 D1 或 SQLite-backed Durable Object：

~~~sql
nodes(
    snapshot_id,
    node_id,
    kind,
    model,
    name,
    payload
);

edges(
    snapshot_id,
    src,
    dst,
    kind,
    payload
);
~~~

必要索引：

~~~sql
CREATE INDEX edges_src_kind
ON edges(snapshot_id, src, kind);

CREATE INDEX edges_dst_kind
ON edges(snapshot_id, dst, kind);
~~~

第一批 HTTP 查询：

- GET /api/v1/models/:model
- GET /api/v1/fields/:model/:field
- POST /api/v1/impact
- POST /api/v1/context
- POST /api/v1/path
- GET /api/v1/overrides/:model/:method

所有遍历必须有 max_depth、max_nodes、超时和结果大小限制。

## 9. 第四阶段：远程 MCP

通过 Streamable HTTP 在 /mcp 提供远程 MCP Server。

优先暴露少量语义化工具：

- inspect_model
- trace_field
- analyze_impact
- discover_context
- find_dependency_path
- explain_override

MCP 工具不应机械映射每个底层 API。每个工具应：

- 对应明确的 Agent 目标。
- 有严格参数 schema。
- 返回结构化证据和必要摘要。
- 包含 snapshot、revision 和数据新鲜度。
- 对空结果、无效模型和截断结果作明确区分。
- 避免将大量原始图数据直接塞入上下文。

公开项目可以允许读取公开快照；私有项目必须使用 OAuth 或 Cloudflare Access。

## 10. 第五阶段：集中 telemetry 与 CI

D1 telemetry 可记录：

- Agent/client 类型。
- tool 名称、目标和 snapshot。
- load、query、serialize 总耗时。
- 结果大小、空结果和截断。
- retry、follow-up 和参数升级。
- 相同 session 内的重复查询。
- context 是否降低了多次探索。

默认不记录：

- 数据库密码、token 和配置文件内容。
- 完整 prompt。
- 与图查询无关的源码或业务数据。

CI 扩展：

1. PR 或发布流程生成新 dump。
2. 上传候选快照。
3. 比较新旧模型、字段、边和 override 链。
4. 生成影响摘要。
5. 将结果交给 Review Agent 或写入 PR 检查。

## 11. 部署顺序

### Phase 0：当前文档

- 保存目标架构和边界。
- 不修改现有 CLI 行为。

### Phase 1：静态项目入口

- 新增 Worker/TypeScript 最小项目。
- 新增静态首页、install.md、llms.txt、manifest.json。
- 使用 Workers Static Assets。
- 配置自定义域名。
- 不创建 D1/R2，不配置业务密钥。

### Phase 2：快照上传

- CLI 新增打包、校验和 publish。
- 配置 R2。
- 引入 snapshot manifest 和 schema version。

### Phase 3：查询 API

- 导入节点/边索引。
- 实现 model、field、impact、context、path。
- 增加缓存、限制和测试。

### Phase 4：MCP

- 将稳定 API 包装成语义化 MCP tools。
- 接入 OAuth/Access。
- 使用 Codex、Cursor 和 MCP Inspector 验证。

### Phase 5：Telemetry 与 CI

- 集中记录工具调用。
- 快照 diff。
- PR 影响报告。
- 基于真实调用数据调整 tool schema。

## 12. 当前 Cloudflare 部署向导说明

当前仓库只有 Python CLI，没有 package.json、wrangler.jsonc 或 Worker 入口。

因此，在 Cloudflare Git 集成向导中直接使用：

~~~text
npx wrangler deploy
~~~

还不足以完成部署。应先在独立提交或分支中加入 Phase 1 的 Worker 项目骨架，再启用自动部署。

第一阶段建议：

- 构建命令：如果直接提交静态文件，可为空；如使用生成器，则填写实际 build 命令。
- 部署命令：npx wrangler deploy。
- 非生产分支部署：可以保留，用于预览。
- API 令牌：可以让 Cloudflare 为 Git 集成自动创建部署令牌。
- Worker 业务环境变量：第一阶段不需要。
- 不要在仓库或普通环境变量中保存 Cloudflare API token；敏感值只能使用加密 secrets。

## 13. 安全与数据治理

Odoo registry dump 通常不包含业务表中的实际记录，但仍可能泄露：

- 私有模块、模型、字段和方法命名。
- 模块依赖和业务架构。
- 本机路径、数据库名和环境标识。
- 自定义实现的结构性信息。

所以必须：

- 默认将企业项目视为私有数据。
- publish 前执行脱敏。
- 区分公开示例快照和私有真实快照。
- 对上传、删除和切换 latest 等写操作使用更严格权限。
- 为 snapshot 设置 schema version 和不可变 revision。
- 保留审计信息和安全的删除流程。

## 14. 近期决策

当前推荐决策：

1. 使用 Workers Static Assets，而不是先做 GitHub Pages 再迁移。
2. 使用自定义域名作为长期入口。
3. 同域提供人类页面、install.md、llms.txt 和 manifest.json。
4. dump 继续在本地/CI/Odoo Pod 执行。
5. Worker 首先只做静态信息站点，之后按阶段增加 R2、D1、API 和 MCP。
6. 中国大陆访问按“先实测、后决定是否需要境内部署/ICP”的方式处理。

## 15. 参考资料

- Cloudflare Workers Static Assets:
  https://developers.cloudflare.com/workers/static-assets/
- Cloudflare Remote MCP:
  https://developers.cloudflare.com/agents/model-context-protocol/
- Cloudflare R2 Workers API:
  https://developers.cloudflare.com/r2/get-started/workers-api/
- Cloudflare D1:
  https://developers.cloudflare.com/d1/
- Cloudflare China Network:
  https://developers.cloudflare.com/china-network/
- llms.txt proposal:
  https://llmstxt.org/
- uv tool installation:
  https://docs.astral.sh/uv/guides/tools/
