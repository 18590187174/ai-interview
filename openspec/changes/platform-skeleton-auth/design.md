# Design

## Context

本仓库目前是全新项目，除两张竞品参考截图外没有任何代码、数据库或部署产物。技术栈已确定：前端 Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router；后端 Python FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + PostgreSQL；认证 JWT（Access + Refresh），密码 Argon2/bcrypt 哈希。

动机见 proposal.md - Why：先建立可运行底座，再逐个叠加业务功能。本变更同时涉及后端、前端、数据库与部署四个层面，且引入认证这一安全敏感机制，因此需要一份设计文档固化技术决策。

## Goals / Non-Goals

**Goals:**

- 提供一个 `docker compose up` 即可启动的前后端 + PostgreSQL 本地环境。
- 让认证相关的安全决策（密码哈希算法、令牌类型与生命周期、刷新令牌轮换与重用检测）在本阶段一次性定下来，避免后续每个功能各自实现。
- 建立后端统一约定：配置外置、统一错误格式、请求追踪、迁移基线，使后续功能只写业务代码。
- 建立前端统一约定：路由守卫、Axios 拦截器（自动续期）、Pinia 用户态。

**Non-Goals:**

- 不做第三方登录（微信/QQ/GitHub OAuth）、手机验证码、邮箱验证激活——留待独立变更。
- 不做角色权限模型（RBAC）、后台管理端——当前只有普通用户一种身份。
- 不做简历上传、解析、押题生成等任何业务功能。
- 不做生产环境部署（K8s、CI/CD、域名证书）——本变更只交付本地与容器化可运行基线。
- 不做国际化、主题切换、埋点分析。

## Decisions

### 决策 1：密码哈希使用 Argon2id，而非 bcrypt 或 PBKDF2

选用 `argon2-cffi` 的 Argon2id。它同时抵抗 GPU/ASIC 暴力破解与侧信道攻击，是当前主流推荐；bcrypt 有 72 字节输入截断的历史包袱；PBKDF2 需要自行调高迭代次数才够安全。

备选：bcrypt（生态更老、兼容性好）被否决的原因同上；Django/Flask 生态常见的 PBKDF2 被否决，因为需要人工调参且抗 GPU 能力弱。

### 决策 2：Access Token 无状态 JWT + Refresh Token 服务端持久化

Access Token 使用签名 JWT，有效期设为 30 分钟，不落库，避免每次请求查库。Refresh Token 使用随机高熵字符串，其哈希值落库并关联用户，有效期 30 天，用于实现吊销、轮换与重用检测。

备选：(a) 全部用无状态 JWT —— 无法中途吊销，登出形同虚设，否决；(b) Refresh Token 也用 JWT 不落库 —— 无法检测重用与强制下线，否决；(c) 全部落库的 opaque token —— 每次请求都要查库，性能与扩展性差，否决。

### 决策 3：Refresh Token 采用轮换 + 重用检测

每次刷新都颁发新 Refresh Token 并吊销旧的。若服务端收到一个已使用过的 Refresh Token（说明令牌可能已泄露），立即吊销该用户当前全部有效 Refresh Token，强制重新登录。这是 OAuth 2.1 与主流实践推荐的做法。

备选：仅轮换不检测重用 —— 泄露的令牌在有效期内仍可被并行使用，否决。

### 决策 4：后端不存储明文 Refresh Token，只存其哈希

库中保存 Refresh Token 的 SHA-256 哈希值。数据库泄露时攻击者无法直接换取 Access Token。由于令牌本身是高熵随机串（而非用户密码），SHA-256 足够，不需要慢哈希（否则每次刷新都要付出高计算成本）。

### 决策 5：前后端分离部署，通过 CORS 白名单 + 同源 Cookie 之外的 Bearer 方案

前端独立 Vite 应用，后端 `/api/v1`。Access Token 存于内存（Pinia），Refresh Token 由后端在登录响应中返回、前端存入 `httpOnly` Cookie 或内存 + 本地持久化二选一。本变更选择：**Refresh Token 写入 `httpOnly` + `Secure` + `SameSite=Strict` Cookie**，Access Token 仅存内存，降低 XSS 窃取风险。

备选：两个令牌都存 `localStorage` —— XSS 一旦发生即全面失守，否决；两个都存 Cookie —— 需要处理 CSRF，且 Access Token 无需持久化，否决。

### 决策 6：统一错误格式采用 `{ code, message, trace_id }`

所有 4xx/5xx 响应返回该结构，前端只需解析一次。`code` 为稳定的业务错误码字符串（如 `EMAIL_ALREADY_REGISTERED`），便于前端做文案映射，不依赖 HTTP 状态码细分。

### 决策 7：迁移工具使用 Alembic，所有模型变更必须伴随迁移脚本

SQLAlchemy 2.0 声明式模型 + Alembic 自动生成迁移。禁止使用 `create_all()` 作为库结构来源（会导致环境间结构漂移）。

### 决策 8：目录结构按「后端 / 前端」双顶层目录划分

```
backend/          # FastAPI：app/api/v1/, app/models/, app/schemas/, app/services/, app/core/, alembic/, tests/
frontend/         # Vue 3：src/views/, src/components/, src/router/, src/stores/, src/api/, tests/
docker-compose.yml
```

备选：monorepo 工具（pnpm workspace / Nx）管理 —— 当前只有两个包，引入成本大于收益，否决。

### 决策 9：测试策略以「认证流程 + 错误格式」为重点，不追求覆盖率数字

后端 Pytest 覆盖注册/登录/刷新/登出/未授权访问/健康检查；前端 Vitest 覆盖路由守卫与令牌续期逻辑。骨架阶段不为凑覆盖率写无意义测试。

## Risks / Trade-offs

- **[风险] Refresh Token 存 Cookie 增加 CSRF 面** → 缓解：`SameSite=Strict` + 仅 `/api/v1/auth/refresh` 端点接受 Cookie 中的令牌，且该端点不做任何状态变更操作；后续可叠加 CSRF Token。
- **[风险] 邮箱作为唯一登录标识，但本阶段不做邮箱验证，可能引发虚假注册与账号抢占** → 缓解：注册后标记邮箱未验证状态字段并预留验证接口位置；后续 change 补发信与验证；短期可接受。
- **[风险] 30 分钟 Access Token 过期在长会话场景（如长时间作答）会造成中断** → 缓解：Axios 拦截器静默续期；若续期失败才跳转登录，且登录后可回到原页面。
- **[风险] Argon2 参数配置不当导致登录接口耗时过高，成为性能瓶颈** → 缓解：参数（time_cost/memory_cost/parallelism）写入配置并针对部署环境调优；登录接口限流。
- **[权衡] 不做 RBAC 意味着后续引入管理端时需要一次迁移** → 接受：当前无管理端需求，避免过度设计；迁移成本可控（加角色字段与权限检查中间件）。
- **[权衡] 占位导航入口先做空页面** → 接受：让外壳与路由结构一次成型，后续 change 只需替换页面内容。

## Migration Plan

本变更为全新项目，不存在线上数据与存量用户，无需数据迁移。上线步骤：

1. 启动 PostgreSQL，执行 `alembic upgrade head` 建立初始库结构。
2. 启动后端服务，确认 `/api/v1/health` 返回正常。
3. 启动前端，确认可注册、登录、刷新、登出，且未登录访问被拦截。
4. 回滚：执行 `alembic downgrade base` 清空结构，回退代码版本即可；无用户数据需要保留。

## Open Questions

- 是否需要用户在注册时勾选并留存同意条款（隐私政策/用户协议）？本阶段先不做，待产品提供文案后作为独立变更处理。
- 是否需要限制同一账号的并发登录设备数？当前允许任意多设备同时登录，若产品后续要求「单设备登录」需新增变更。
