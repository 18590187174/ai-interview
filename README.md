# AI 模拟面试平台

面向求职者的 AI 模拟面试与面试准备平台。当前阶段交付**平台骨架与认证**：可运行的工程底座、用户体系、统一导航外壳，后续功能以独立变更逐个叠加。

## 核心业务主线

```
简历押题 → 开始面试 → 面试报告 → 我的（历史回看）
```

1. **简历押题**：填写目标岗位、工作年限、岗位描述、编程语言（可选），上传简历后结合知识库生成最可能被问到的题目。
2. **开始面试**：一问一答模拟真实面试，支持打字与语音作答。
3. **面试报告**：给出评分、参考答案与针对实际回答的改进建议。
4. **我的**：回看每次面试的评分、问答与建议。

导航：首页、开始面试、简历押题、知识库、我的。其中「开始面试」「简历押题」「知识库」在当前阶段为占位页面。

## 技术栈

| 层 | 选择 |
| --- | --- |
| 前端 | Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 |
| 数据库 | PostgreSQL 16 |
| 认证 | JWT（Access Token 内存持有 + Refresh Token httpOnly Cookie） |
| 密码 | Argon2id |
| 测试 | pytest（后端） / vitest（前端） |

## 目录结构

```
backend/
  app/
    api/v1/          # 路由与端点
    core/            # 配置、错误处理、日志、追踪、数据库
    models/          # SQLAlchemy 模型
    schemas/         # Pydantic 数据结构
    services/        # 业务逻辑（密码、令牌、用户、认证）
    main.py          # 应用入口
  alembic/           # 数据库迁移
  tests/
frontend/
  src/
    api/             # Axios 封装与接口调用
    layouts/         # 应用外壳
    views/           # 页面
    stores/          # Pinia 状态
    router/          # 路由与守卫
  tests/
docs/api.md          # 认证接口契约
docs/deploy.md       # 本地与线上（腾讯云）部署指南
pack-deploy.ps1      # 生成部署代码包
openspec/            # 规格与变更提案
```

## 环境要求

- Python 3.11+（已验证 3.13）
- Node.js 20.19+（已验证 Node 22）
- PostgreSQL 16（或使用 Docker Compose 一键启动）
- Docker（可选，用于容器化启动）

### 本地数据库（Windows 免安装版，可选）

不想安装系统服务时，可使用 PostgreSQL 官方免安装 ZIP（无需管理员权限）：

```powershell
# 1. 下载并解压（以 16.9 为例，可自行换版本与目录）
curl.exe -L -o pgsql.zip https://get.enterprisedb.com/postgresql/postgresql-16.9-1-windows-x64-binaries.zip
Expand-Archive pgsql.zip -DestinationPath D:\tools\pgsql

# 2. 初始化数据目录（密码写入 pwfile）
Set-Content pwfile.txt -Value "postgres" -Encoding ascii -NoNewline
D:\tools\pgsql\pgsql\bin\initdb.exe -D D:\tools\pgdata -U postgres --pwfile=pwfile.txt -E UTF8 --auth=scram-sha-256

# 3. 启动 / 停止
D:\tools\pgsql\pgsql\bin\pg_ctl.exe -D D:\tools\pgdata -l D:\tools\pgdata\server.log start
D:\tools\pgsql\pgsql\bin\pg_ctl.exe -D D:\tools\pgdata stop

# 4. 建库
D:\tools\pgsql\pgsql\bin\psql.exe -U postgres -h 127.0.0.1 -c "CREATE DATABASE ai_interview;"
```

对应 `DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/ai_interview`。

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
cp .env.example .env      # 按需修改，生产环境务必替换 JWT_SECRET_KEY
docker compose up --build
```

- 前端：http://localhost:8080
- 后端：http://localhost:8000/docs

### 方式二：本地开发

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp ../.env.example .env        # 填写 DATABASE_URL 与 JWT_SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
cp ../.env.example .env        # 设置 VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev
```

开发模式下 Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，不配代理变量也可直接联调。

线上（腾讯云 + 宝塔 + HTTPS）部署与更新步骤见 [docs/deploy.md](docs/deploy.md)。

## 数据库迁移

```bash
cd backend
alembic revision --autogenerate -m "说明"   # 生成迁移
alembic upgrade head                        # 升级
alembic downgrade -1                        # 回滚一版
```

库结构**只**通过迁移变更，禁止使用 `create_all()` 作为结构来源。

## 测试

```bash
cd backend && pytest          # 后端：37 个用例（默认内存 SQLite）
cd frontend && npm run test   # 前端：15 个用例
cd frontend && npm run build  # 类型检查 + 生产构建
```

后端测试默认使用内存 SQLite；如需在真实 PostgreSQL 上验证方言兼容性（CI 推荐）：

```bash
cd backend
export TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/ai_interview"
pytest
```

## 环境变量

完整清单见 `.env.example`。关键点：

- `JWT_SECRET_KEY`：**必填**，缺失时服务拒绝启动并提示缺失项。
- `DATABASE_URL`：PostgreSQL 连接串。
- `CORS_ORIGINS`：允许的前端来源，多个用逗号分隔。
- `COOKIE_SECURE` / `COOKIE_SAMESITE`：生产环境建议 `true` / `strict`。
- `VITE_API_BASE_URL`：前端后端接口地址。

## 安全约定

- 密码使用 Argon2id 加盐哈希存储，响应中永不返回密码或哈希。
- 访问令牌仅保存在内存；刷新令牌由服务端以 `httpOnly` Cookie 下发，库中只存其哈希。
- 刷新令牌每次使用即轮换；检测到重用时吊销该用户全部会话。
- 错误响应统一为 `{code, message, trace_id}`，服务端异常不向调用方泄露堆栈与内部细节。

## 接口文档

启动后端后访问 http://localhost:8000/docs ，契约说明见 `docs/api.md`。

## 开发流程

本项目使用 OpenSpec 进行规格驱动开发：

```bash
openspec list                       # 查看进行中的变更
/opsx:propose <name>                # 创建变更提案（先定规格再写代码）
/opsx:apply                         # 按任务清单实现
/opsx:archive                       # 归档并合并到 openspec/specs/
```

**工具平台相关页面**：

首页：

![image-20261027114244290](C:\Users\LHC\AppData\Roaming\Typora\typora-user-images\image-20261027114244290.png)

核心功能页：

![image-20261027114335118](C:\Users\LHC\AppData\Roaming\Typora\typora-user-images\image-20261027114335118.png)

![image-20261027114443482](C:\Users\LHC\AppData\Roaming\Typora\typora-user-images\image-20261027114443482.png)
