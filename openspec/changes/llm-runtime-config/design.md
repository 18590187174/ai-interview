# Design

## Context

押题（`question-prediction`）已实现，凭据来自 `Settings.llm_api_key`（启动时读取环境变量）。设置页（`system-dictionary-config`）已有字典管理。本变更让凭据可运行时配置。

## Goals / Non-Goals

Goals:

- 凭据可从设置页配置、更新、清除，保存即生效
- 凭据在接口层脱敏，完整 Key 永不出现在任何响应中
- 环境变量配置保持兼容（作为兜底来源）

Non-Goals:

- 多模型配置档、按用户隔离的 Key（平台级共享，与字典一致）
- 加密存储（见决策 2 的取舍）
- 其他系统设置的通用管理界面（本次仅 LLM 凭据；键值存储结构可复用）

## Decisions

### 1. 键值表存储，数据库覆盖优先于环境变量

`app_settings` 表（`key` 为主键的 String 键值对），键：`llm_api_key` / `llm_base_url` / `llm_model`。解析优先级：数据库有值 → 用数据库；否则回落环境变量；两者皆无 → 押题返回 503。`Settings`（环境配置）其余项（超时、温度等）不开放运行时覆盖。

备选：把 Key 写进 `.env` 文件。拒绝理由：容器环境文件系统常为只读，且覆写配置文件易引入格式损坏。

### 2. API Key 明文入库（接受的取舍）

调用大模型必须还原完整 Key；对称加密需要再管理一个主密钥，单机部署下主密钥仍在同一台机器/同一环境变量里，防护增益有限。接受明文存储，防护措施为：接口层永不回显完整 Key、日志中不打印凭据、数据库文件访问权限与部署环境等同。若未来引入密钥管理服务，可在此表上平滑替换。

### 3. 响应脱敏规则

`api_key_masked = "***" + key 末 4 位`（Key 长度 ≤4 时不展示末位，仅返回 `***`）。`source` 取 `database` / `environment` / `none`，帮助用户判断当前生效来源。

### 4. LLM 服务消费「运行时配置」而非 Settings

新增 `LLMRuntimeConfig`（api_key / base_url / model），由 `system-settings` 服务解析（DB > env）后传入 `LLMClient`。`LLMClient` 抽象不变，测试桩不受影响。

## Risks / Trade-offs

- [数据库泄露即凭据泄露] → 明文存储是显式取舍；文档标注生产环境建议用环境变量并限制数据库访问
- [多人共享平台时任意用户可改 Key] → 与字典一致的取舍（无角色体系）；引入角色后收紧写权限
- [Base URL 配置错误导致押题失败] → 保存时校验 URL 格式；调用失败仍返回 `MODEL_UNAVAILABLE` 并记录日志

## Open Questions

- 是否需要「测试连接」按钮（发一次廉价探测请求验证 Key 有效性）——留待使用反馈
- Key 轮换提醒（如 90 天）——暂不做
