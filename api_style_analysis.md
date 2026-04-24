# JSON-RPC vs REST：对外 API 风格讨论

## 1. 现状盘点

审查了代码后，当前 API 层的全貌如下：

### 1.1 三类 API 受众

| 受众 | 认证方式 | 路由前缀 | 示例 | 端点数量（约） |
|------|---------|---------|------|-------------|
| 内部 VB 系统 | `auth='public'`（无认证） | `/factoring_api/` | `factoring_api.py` | ~2 |
| 外部客户 OpenAPI | `auth='openapi'`（Token+APIKey） | `/openapi/` | `ifs_gar_entry`, `ifs_gar_trade`, `ifs_gar_account` 等 | ~30+ |
| 小程序前端 | `auth='openapi'` | `/openapi/miniapp/` 或共用 `/openapi/` | `ifs_gar_invite` | ~5+ |

所有 `type='json'` 的端点都使用 JSON-RPC 信封格式。

### 1.2 认证基础设施（关键发现）

审查 [galaxy_open_api/models/ir_http.py](file:///home/inoryzzz/Odoo/addons-oabay/galaxy_open_api/models/ir_http.py) 后，有一个重要发现：

**`auth="openapi"` 认证方法并不绑定 JSON-RPC。** 它是 Odoo 的通用 auth method，对 `type='json'` 和 `type='http'` 路由都有效。代码中已经有先例——`/openapi/merchant/credit_sign` 就是 `type='http'` + `auth='openapi'` 的组合。

```python
# 已有的 type='http' + auth='openapi' 先例
@route(['/openapi/merchant/credit_sign'], type='http', auth="openapi", ...)
```

但是有两个地方硬编码了 JSON-RPC 的假设：
1. **`_handle_error`**：检查 `/openapi` 路径前缀，强制返回 `{"jsonrpc": "2.0", "error": {...}}` 格式
2. **`_post_dispatch`**：检查 `/openapi` 路径前缀，解析 JSON-RPC 格式记录响应日志

这意味着：**迁移到 REST 风格时，认证体系本身兼容，但错误处理和日志需要适配。**

### 1.3 当前控制器的真实痛点

比起 JSON-RPC vs REST 的选择，我在审查代码中观察到几个更紧迫的问题：

1. **控制器文件巨大且包含大量业务逻辑**
   - `ifs_gar_entry/controllers/openapi.py`：1455 行
   - `ifs_gar_trade/controllers/openapi.py`：1245 行
   - 大量的参数校验、状态迁移、记录创建、消息推送逻辑直接写在控制器里

2. **错误处理不一致**
   - 有的端点直接 `raise UserError`（依赖 `_handle_error` 转换）
   - 有的端点 try/catch 后返回 `{'error_msg': str(e)}`
   - HTTP 状态码始终是 200，错误信息藏在 body 里

3. **多个控制器类同名** `OpenApiController` 散落在不同模块

---

## 2. 逐维度分析

### 2.1 调用方便利性（Developer Experience for Consumers）

| 维度 | JSON-RPC | REST |
|------|---------|------|
| 请求格式 | 需要 `{"jsonrpc":"2.0","method":"call","params":{...},"id":1}` 信封 | 直接发送业务 JSON body |
| 响应格式 | 业务数据嵌套在 `result` 里，错误嵌套在 `error` 里 | 业务数据即顶层 body，HTTP 状态码区分成功/失败 |
| 错误判断 | 需解析 body 中的 `error` 字段（HTTP 始终 200） | 标准 HTTP 状态码 (400/401/403/404/409/500) |
| API 文档 | 无标准规范，需手写文档 | OpenAPI/Swagger 规范，可自动生成可交互文档 |
| 工具支持 | 需要理解 JSON-RPC 协议才能用 Postman/curl | curl/Postman/各语言 SDK 开箱即用 |
| 缓存 | 所有请求是 POST，无法 HTTP 缓存 | GET 请求天然可缓存 |

**结论：REST 在调用方体验上有显著优势，尤其是对外部客户和前端开发者。** JSON-RPC 的信封对不熟悉 Odoo 的外部调用方是纯粹的噪音。

### 2.2 开发体验（Developer Experience for You）

| 维度 | JSON-RPC (当前) | REST (迁移后) |
|------|----------------|-------------|
| 参数获取 | Odoo 自动从 `params` 解包到函数参数 | 需要自己从 `request.get_json_data()` 解析（或用框架） |
| 响应序列化 | 自动包装到 `result` | 需要 `request.make_json_response(data)` |
| 错误处理 | `raise UserError` 自动被 `_handle_error` 捕获 | 需要自己构建错误响应或写统一装饰器 |
| Odoo 集成 | 原生，零摩擦 | 需要额外适配层 |
| 新端点成本 | 几乎为零（复制粘贴 route 装饰器） | 略高（需要手动处理 request/response） |

**结论：JSON-RPC 在 Odoo 内的开发效率更高。** 切到 REST 需要补一层轻量适配，但这个成本是一次性的。

### 2.3 长期可维护性与可扩展性

| 维度 | JSON-RPC | REST |
|------|---------|------|
| API 版本化 | 无标准做法，只能靠路径或参数 | 标准做法：URL 前缀 (`/api/v1/`, `/api/v2/`) 或 Accept Header |
| 契约稳定性 | 信封格式固定，但内部结构无约束 | 可用 OpenAPI Schema 做契约测试 |
| 多端复用 | 所有端复用同一种调用方式（好处也是坏处） | 可根据受众做不同版本/视图 |
| 监控/可观测性 | 路径全是 POST，只能靠 body 内容区分 | 路径+方法天然可区分，日志/监控更清晰 |
| 限流 | 只能靠路径+body 解析 | 基于路径+方法，标准工具直接支持 |

**结论：REST 在长期治理上更有优势。** 但前提是你投入了构建适配层的成本。

### 2.4 认证体系兼容性（你特别关心的问题）

经过审查，明确结论：

> **`X-GALAXY-ACCESS-TOKEN` + `X-GALAXY-API-KEY` 认证体系完全兼容 REST 风格。**

原因：
- `_auth_method_openapi` 只从 HTTP headers 读取 token 和 apikey
- 它通过 `res.users.apikeys._check_credentials` 验证凭据
- 然后通过 `request.update_env(user=user_id)` 设置 Odoo 用户上下文
- 这整个流程与请求是 `type='json'` 还是 `type='http'` 完全无关

**需要适配的两处：**

```python
# 1. _handle_error 中 — 需要区分 JSON-RPC 和 REST 端点的错误格式
if request.httprequest.path.startswith('/openapi'):
    # 当前：统一返回 JSON-RPC 格式
    # 需要：判断是否 REST 端点，返回对应格式

# 2. _post_dispatch 中 — 日志记录假设了 JSON-RPC 格式
jsonrequest = json.loads(request.httprequest.data.decode('utf-8'))
openapi_log_id = jsonrequest.get('openapi_log_id')
# 需要：REST 端点使用不同的日志注入方式（如 request 属性）
```

改动量很小，且可以做到向后兼容——旧的 JSON-RPC 端点不受影响。

---

## 3. 可选方案对比

### 方案 A：维持现状（JSON-RPC）

- **做什么**：不动传输协议，专注于把业务逻辑从 controller 抽到 model
- **优点**：零迁移成本，团队无学习成本
- **缺点**：对外 API 的体验问题持续存在
- **适用**：如果外部客户/小程序端都由你们控制，且接受 JSON-RPC

### 方案 B：Odoo 原生 `type='http'` + 轻量装饰器（推荐）

不引入任何第三方框架，用 Odoo 原生能力实现 REST 风格：

```python
# 一个极简的 REST 适配装饰器示例
import functools, json
from odoo.http import request, Response
from odoo.exceptions import UserError, AccessDenied, ValidationError

def rest_api(func):
    """将 Odoo controller 方法适配为 REST 风格的 JSON API。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 解析 JSON body
        try:
            body = request.get_json_data() if request.httprequest.content_type == 'application/json' else {}
        except Exception:
            body = {}
        kwargs.update(body)

        try:
            result = func(*args, **kwargs)
            return request.make_json_response(
                {'success': True, 'data': result},
                status=200,
            )
        except UserError as e:
            return request.make_json_response(
                {'success': False, 'error': {'code': 'BUSINESS_ERROR', 'message': str(e)}},
                status=400,
            )
        except AccessDenied as e:
            return request.make_json_response(
                {'success': False, 'error': {'code': 'ACCESS_DENIED', 'message': str(e)}},
                status=403,
            )
        except ValidationError as e:
            return request.make_json_response(
                {'success': False, 'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}},
                status=422,
            )
        except Exception:
            return request.make_json_response(
                {'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': '系统异常'}},
                status=500,
            )
    return wrapper

# 使用示例
class MerchantInviteAPI(Controller):
    @route('/api/v1/merchant/invite/init', type='http', auth='openapi',
           methods=['POST'], cors='*', csrf=False)
    @rest_api
    def invite_init(self, supplier_code, factor_code, company_name, ...):
        supplier, factor = self._resolve_supplier_factor(supplier_code, factor_code)
        # ... 业务逻辑 ...
        return {'invite_merchant_id': invite.id, 'ifs_company_id': ifs_company.id}
```

- **优点**：
  - 零外部依赖，完全用 Odoo 原生能力
  - 装饰器一次性开发，所有新端点复用
  - 认证体系 (`auth='openapi'`) 零改动
  - 旧 JSON-RPC 端点完全不受影响（共存）
  - 新端点返回标准 HTTP 状态码
  - 可渐进迁移，不需要一次性切换

- **缺点**：
  - 参数解析不如 JSON-RPC dispatcher 自动（需在装饰器中处理）
  - 没有自动生成 OpenAPI 文档的能力（需手写或用其他工具）
  - 需要小幅修改 `_handle_error` 避免 REST 端点被覆盖成 JSON-RPC 格式

### 方案 C：OCA `odoo-fastapi`

引入 OCA 的 [odoo-fastapi](https://github.com/OCA/rest-framework/tree/17.0/fastapi) 模块：

- **优点**：
  - 生产级 REST 框架，Pydantic 做参数校验和序列化
  - 自动生成 OpenAPI/Swagger 文档
  - 社区维护，长期有人跟进
  - FastAPI 的生态（依赖注入、中间件等）
- **缺点**：
  - 引入较重的依赖链（FastAPI, Pydantic, uvicorn workaround 等）
  - Odoo 17 的 OCA fastapi 模块成熟度需要验证
  - 认证体系需要桥接——你的 `_auth_method_openapi` 逻辑需要迁移为 FastAPI 的 Depends
  - 学习曲线：团队需要理解 FastAPI + Odoo 的集成方式
  - 与现有 `ir_http` 层的错误处理/日志机制需要重新对接

### 方案 D：OCA `base_rest` (不推荐)

- Odoo 14-16 时代的产物，Odoo 17 上的支持不确定
- 被 `odoo-fastapi` 逐步取代
- 不建议在新项目中采用

---

## 4. 我的建议

### 优先级判断

结合你的项目上下文（早期阶段、业务规则还在演进、外部客户+小程序两个对外场景）：

```
紧急度排序：
1. [高] 控制器中的业务逻辑下沉到 model     ← 这是架构红线问题
2. [中] 新的对外端点采用 REST 风格           ← 这是本次讨论的主题
3. [低] 已有端点从 JSON-RPC 迁移到 REST     ← 按需渐进，不急
```

### 推荐路径：方案 B（原生 REST 装饰器）+ 渐进迁移

理由：

1. **不引入新依赖** — 你的项目还在早期，依赖链应该尽可能短。方案 C (FastAPI) 的价值主要在自动文档和参数校验，但代价是一整条新的技术栈。在你当前的规模（~30 个端点）下，这个 ROI 不划算。

2. **认证零改动** — `auth='openapi'` 直接复用，`_handle_error` 只需加一个路径判断分支。

3. **可渐进** — 新端点用 `/api/v1/` 前缀 + REST 风格，旧端点 `/openapi/` 继续跑 JSON-RPC。不需要大爆炸迁移。等业务稳定后，外部客户可以逐步切到新端点。

4. **倒逼好的设计** — REST 装饰器天然要求 controller 只做参数解析和返回映射，业务逻辑必须在 model 里。这和你的架构红线方向一致。

### 具体执行步骤（如果决定推进）

```
Phase 0: 准备（~1天）
├── 在 galaxy_open_api 中创建 rest_api 装饰器
├── 修改 _handle_error：对 /api/ 前缀不套 JSON-RPC 信封
└── 修改 _post_dispatch：对 /api/ 前缀用 request 属性而非 body 注入日志 ID

Phase 1: 试点（选 1-2 个端点）
├── 选一个简单的查询端点（如 merchant_state）用 REST 风格重写
├── 新旧端点并存，验证认证/日志/错误处理都正常
└── 让小程序/外部客户试调新端点

Phase 2: 新端点默认 REST
├── 所有新端点走 /api/v1/ + REST 风格
├── 编写 API 文档模板
└── 旧端点按需迁移（优先迁移外部客户常用的）
```

### 关于小程序 vs 外部客户是否需要不同风格

不需要。两者都是 HTTP 调用方，统一用 REST 即可。小程序端如果已经适配了 JSON-RPC 信封，可以在旧端点上继续跑，不强制迁移。

---

## 5. 需要你决策的问题

1. **你的外部客户对当前 JSON-RPC 格式有多少抱怨？** 如果客户已经适配了且没有痛感，迁移的紧迫性会降低。

2. **小程序前端是你们自己的团队开发吗？** 如果是，切换成本更可控。

3. **你是否愿意接受新旧端点并存一段时间？** 方案 B 的核心前提是渐进迁移。

4. **业务逻辑下沉是否已经在推进？** 如果 controller 里的逻辑还没有开始往 model 迁移，我建议先做这个，再考虑 REST 化。因为如果先做 REST 化但 controller 里还是大量业务逻辑，你只是换了一层皮，核心问题没解决。
