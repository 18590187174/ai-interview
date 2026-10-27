# Spec Delta

## Purpose

提供运行时系统设置的键值存储与 LLM 凭据管理：用户可在设置页配置模型访问凭据，保存后押题立即生效，无需重启服务；凭据在任何接口中不以完整形式暴露。

## ADDED Requirements

### Requirement: LLM 凭据状态查询

系统 SHALL 提供凭据状态查询，返回「是否已配置、脱敏掩码（`***` + 末 4 位）、当前 Base URL、模型名、来源（数据库/环境变量）」；任何响应 MUST NOT 包含完整的 API Key。

#### Scenario: 已配置时返回脱敏掩码

- **WHEN** 已保存以 `sk-` 开头的 API Key 后查询凭据状态
- **THEN** 响应中 `has_api_key` 为真，`api_key_masked` 仅含掩码与末 4 位，不含完整 Key

#### Scenario: 未配置时返回来源标记

- **WHEN** 数据库与环境变量均未配置 Key 时查询
- **THEN** 响应中 `has_api_key` 为假且 `source` 为 `none`

#### Scenario: 未登录查询被拒绝

- **WHEN** 未携带有效访问令牌查询凭据状态
- **THEN** 系统返回 401 与错误码 `UNAUTHORIZED`

### Requirement: LLM 凭据更新

系统 SHALL 提供凭据更新：API Key 未传入时保持不变、传入空串时清除；Base URL 与模型名未传入时保持不变、传入空串时恢复服务端默认；Base URL MUST 为合法 HTTP(S) 地址。

#### Scenario: 更新 API Key

- **WHEN** 用户提交新的 API Key
- **THEN** 系统保存后返回更新后的脱敏状态，且不回显完整 Key

#### Scenario: 不修改 Key 只改模型名

- **WHEN** 用户仅提交模型名而未传 API Key
- **THEN** 已有 Key 保持不变，模型名更新

#### Scenario: 清除 API Key

- **WHEN** 用户提交空串 API Key
- **THEN** 数据库覆盖被清除，凭据来源回落到环境变量（若有）或 `none`

#### Scenario: 非法的 Base URL

- **WHEN** 用户提交非 HTTP(S) 格式的 Base URL
- **THEN** 系统返回 422 与错误码 `VALIDATION_ERROR`

### Requirement: 凭据运行时生效

系统 SHALL 按「数据库覆盖 > 环境变量」的优先级解析押题所用的凭据；保存后 MUST 无需重启即可生效。

#### Scenario: 保存后押题立即可用

- **WHEN** 此前押题返回 503（未配置凭据），用户保存有效凭据后再次发起押题
- **THEN** 押题流程使用新凭据调用大模型，不再返回「未配置凭据」错误

#### Scenario: 数据库覆盖环境变量

- **WHEN** 环境变量与数据库中均存在 API Key
- **THEN** 押题使用数据库中的 Key

### Requirement: 设置页模型配置入口

系统 SHALL 在设置页提供「模型配置」区块：API Key 密文输入（占位符展示脱敏掩码）、Base URL、模型名与保存按钮；未登录访问被路由守卫拦截。

#### Scenario: 在设置页配置凭据

- **WHEN** 用户在设置页填写 API Key 并保存
- **THEN** 页面展示保存后的脱敏掩码，且不回显完整 Key

#### Scenario: 未登录访问设置页

- **WHEN** 未登录用户访问设置页
- **THEN** 路由守卫将其重定向到登录页并记录原目标地址
