# Tasks

> 图例：`- [x]` = 已完成（部分预览主题会将其渲染成叉，属显示差异），`- [ ]` = 未完成。

## 1. 后端角色与权限

- [x] 1.1 `users` 模型新增 `is_admin` 列并生成迁移 `98abedf1f660`（存量数据回填 false）；`/users/me` 响应返回 `is_admin`；补测试
- [x] 1.2 应用启动 lifespan 幂等创建默认管理员 `admin@qq.com`（Argon2 哈希、邮箱已验证、is_admin），验证不存在时创建、已存在时不覆盖
- [x] 1.3 新增 `require_admin` 依赖（403 `FORBIDDEN`），挂载到字典写端点与 LLM 设置读写端点（字典读取保持登录用户可读），验证非管理员 403、管理员正常、未登录 401 的测试通过

## 2. 前端角色控制

- [x] 2.1 用户 store 暴露 `isAdmin`（来自 `/users/me`），顶栏设置入口仅管理员渲染
- [x] 2.2 路由 `/settings` 增加 `requiresAdmin` 元信息，守卫拦截非管理员重定向首页；非管理员调用设置接口时页面展示 403 错误信息

## 3. 验证

- [x] 3.1 端到端验证：默认管理员登录 → 设置页可管理字典与凭据；普通用户无入口、直接调接口 403、押题向导字典读取正常
- [x] 3.2 运行 `openspec validate admin-role-access --strict`，验证 delta spec 通过校验
