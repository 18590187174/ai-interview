# Proposal

## Why

AI 模拟面试平台目前无任何代码，仅有一份竞品（面多多）参考截图。在动手实现「简历押题」等具体业务功能前，必须先建立可运行的工程骨架与用户体系：没有统一的项目结构、配置管理、数据库迁移基线和认证机制，后续每个功能都会重复造轮子，且用户数据（简历属敏感个人信息）无法归属到账号、无法做访问控制。

本变更的目标是交付一个「能跑、能登录、能扩展」的最小平台底座，让后续「简历押题」「快速面试」等功能以独立变更的方式逐个叠加。

## What Changes

- 新建后端工程骨架：FastAPI 应用入口、`/api/v1` 路由前缀、配置管理（环境变量驱动，区分 dev/test/prod）、统一响应与错误格式、健康检查端点、结构化日志、CORS 与请求 ID 中间件。
- 建立数据层基线：SQLAlchemy 2.0 模型基类（含 `id`、`created_at`、`updated_at`）、Alembic 迁移环境与初始迁移、数据库连接会话管理。
- 新增用户体系与认证：用户注册、登录（邮箱 + 密码）、登出、刷新令牌、获取当前用户信息；密码使用 Argon2 哈希存储；JWT Access Token（短期）+ Refresh Token（长期，可轮换与吊销）。
- 新增前端工程骨架：Vue 3 + Vite + TypeScript 项目、Element Plus 主题、Pinia 状态管理、Vue Router 路由表与登录态路由守卫、Axios 封装（自动携带与刷新令牌）。
- 新增应用外壳（App Shell）：顶部导航与侧边栏布局，导航项为首页、开始面试、简历押题、知识库、我的；其中「开始面试」「简历押题」「知识库」在本变更中为占位页面，「首页」「我的」为可用页面，未登录时访问受保护页面跳转登录页。
- 建立质量与交付基线：Pytest（后端）+ Vitest（前端）测试脚手架、Ruff + ESLint 配置、前后端 Dockerfile 与 docker-compose（应用 + PostgreSQL）、README 启动说明。

不涉及（后续变更处理）：简历上传与解析、押题生成、真实面试会话、题库内容、支付与邀请奖励。

## Capabilities

### New Capabilities

- `user-auth`: 用户注册、登录、登出、令牌刷新与当前用户信息获取，以及密码存储与令牌安全策略。
- `app-shell`: 前端统一导航外壳与基于登录态的路由访问控制。
- `platform-foundation`: 后端工程骨架与可观测性基线（配置管理、健康检查、统一错误格式、请求追踪、数据库迁移基线）。

### Modified Capabilities

无（本仓库当前没有任何已存在的 spec）。

## Impact

- 新增代码：后端 `backend/`（FastAPI）、前端 `frontend/`（Vue 3）、部署文件 `docker-compose.yml` 及各服务 `Dockerfile`。
- 新增依赖：后端 fastapi、uvicorn、sqlalchemy、alembic、pydantic-settings、psycopg、argon2-cffi、python-jose 或 pyjwt、pytest；前端 vue、vite、element-plus、pinia、vue-router、axios、vitest。
- 新增基础设施：PostgreSQL 数据库实例与 Alembic 迁移基线。
- 新增 API：`/api/v1/auth/*` 系列端点、`/api/v1/health`、`/api/v1/users/me`；OpenAPI 文档自动可用。
- 存储：新增 `users` 表（含邮箱唯一约束）与 `refresh_tokens` 表（或等价的令牌吊销记录）。
- 配置项：数据库连接串、JWT 密钥与有效期、CORS 允许的源、日志级别——均通过环境变量注入，禁止硬编码密钥。
