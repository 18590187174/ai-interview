# Proposal

## Why

设置功能（字典管理、LLM 凭据配置）是平台级配置，当前任何登录用户都可修改，存在误操作与凭据泄露面。需要引入管理员角色：设置功能仅管理员可用，并预置默认管理员账号。

## What Changes

- 用户模型新增 `is_admin` 角色标记（默认普通用户）；当前用户信息接口返回该标记
- 应用启动时幂等创建默认管理员：`admin@qq.com`（密码 `admin123`，邮箱已验证）——已存在则跳过，不覆盖已有数据
- 端点权限收紧（**BREAKING** 行为变更）：
  - 字典**写**操作（新增/删除）与 LLM 设置**读写**：仅管理员，非管理员返回 403 `FORBIDDEN`
  - 字典**读**操作（按类型/全量）：保持登录用户可读（押题向导依赖）
- 前端：设置页入口仅对管理员显示；路由守卫拦截非管理员访问 `/settings`；用户信息含角色用于渲染
- 安全取舍（显式记录）：默认密码 `admin123` 为弱密码（不满足注册接口的复杂度要求，种子创建不走该校验），首次部署后应立即修改

## Capabilities

### New Capabilities

- `user-roles`：用户角色与管理员保护（角色标记、默认管理员种子、设置端点权限、前端入口控制）

### Modified Capabilities

无。`system-settings` 与 `system-dictionary` 的功能行为不变，仅访问控制层收紧（其 delta 描述的"登录用户可操作"由本变更取代，归档顺序上本变更后于二者合并）。

## Impact

- 后端：`users` 表加 `is_admin` 列（迁移）；`deps.py` 新增 `require_admin` 依赖；`dictionaries` 写端点与 `system_settings` 全部端点挂载该依赖；应用启动 lifespan 增加默认管理员种子；`/users/me` 响应增加 `is_admin`
- 前端：用户 store 增加 `isAdmin`；`MainLayout` 设置入口按角色渲染；路由守卫增加 `requiresAdmin` 元信息校验
- 测试：非管理员 403 用例、管理员正常用例、种子幂等用例
- 风险：默认凭据公开（本文档即含）——生产部署必须立即修改密码
