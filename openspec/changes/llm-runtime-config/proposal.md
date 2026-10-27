# Proposal

## Why

大模型访问凭据（`LLM_API_KEY`）目前只能通过环境变量在启动前配置，用户在页面上触发押题只会看到「未配置大模型访问凭据」的报错，却无处可配——必须改 `.env` 并重启服务，体验断裂。需要在设置页提供凭据的运行时配置入口，保存后立即生效。

## What Changes

- 新增运行时系统设置能力：`app_settings` 键值表存储 LLM 相关覆盖项（API Key、Base URL、模型名）
- 新增端点：`GET /api/v1/settings/llm`（凭据状态：是否已配置、脱敏掩码、当前 Base URL 与模型名）、`PUT /api/v1/settings/llm`（更新凭据；不传 Key 则保持不变，传空串则清除）
- **任何接口 SHALL NOT 返回完整的 API Key**，只返回 `sk-***` + 末 4 位的脱敏掩码
- 凭据解析优先级：数据库覆盖 > 环境变量；保存后押题立即使用新凭据，无需重启服务
- 押题未配置凭据的报错文案改为引导「请前往设置页配置」
- 设置页新增「模型配置」区块（API Key 密文输入、Base URL、模型名、保存）

## Capabilities

### New Capabilities

- `system-settings`：运行时系统设置（键值存储、LLM 凭据的读取/更新与脱敏展示、生效优先级）

### Modified Capabilities

无。`question-prediction` 的押题行为本身不变（仍以「有凭据则生成、无凭据 503」为契约），仅凭据的来源扩展为「环境变量或数据库覆盖」。

## Impact

- 后端：新增 `app_settings` 表与迁移；新增 `settings` 端点组；LLM 服务改为消费「运行时凭据」而非直接读环境配置
- 前端：设置页新增模型配置区块（`api/settings.ts`）
- 安全：Key 在数据库中明文存储（单机部署场景的取舍，见 design），接口层脱敏；`.env` 中的 Key 保持兼容（作为兜底）
- 契约文档：`docs/api.md` 追加系统设置部分
