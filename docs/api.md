# 认证接口契约

基础路径：`/api/v1`，所有请求与响应均为 `application/json`。

## 通用约定

### 统一错误格式

所有非 2xx 响应：

```json
{
  "code": "EMAIL_ALREADY_REGISTERED",
  "message": "该邮箱已被注册",
  "trace_id": "9f2c1a..."
}
```

参数校验失败时额外返回 `details`：`[{"field": "password", "message": "..."}]`。
服务端异常统一返回 `code = INTERNAL_ERROR`，不泄露堆栈与内部实现细节。

### 请求追踪

- 每次响应都带 `X-Trace-Id` 响应头；请求方可自带 `X-Trace-Id`，服务端沿用该值。
- 排障时提供 `trace_id` 即可定位单次请求的全部日志。

### 认证方式

- 受保护接口需请求头 `Authorization: Bearer <access_token>`。
- `access_token` 有效期 30 分钟，前端仅在内存中保存。
- `refresh_token` 由服务端通过 `httpOnly` Cookie 下发（路径 `/api/v1/auth`），
  非浏览器客户端可在请求体中显式传 `refresh_token` 字段。

## 错误码

| code | HTTP | 含义 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 请求参数校验失败 |
| `UNAUTHORIZED` | 401 | 缺少访问令牌，或用户不存在 |
| `INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 |
| `EMAIL_ALREADY_REGISTERED` | 409 | 邮箱已被注册 |
| `TOKEN_INVALID` | 401 | 访问令牌或刷新令牌无效 |
| `TOKEN_EXPIRED` | 401 | 令牌已过期 |
| `REFRESH_TOKEN_REUSED` | 401 | 刷新令牌被重用，已吊销该用户全部会话 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `SERVICE_UNAVAILABLE` | 503 | 依赖（数据库）不可用 |
| `INTERNAL_ERROR` | 500 | 服务内部错误 |

---

## POST /api/v1/auth/register

注册新用户。

请求体：

```json
{ "email": "candidate@example.com", "password": "Passw0rd1" }
```

- `email`：合法邮箱，最长 320 字符，全库唯一（不区分大小写）。
- `password`：至少 8 位，且同时包含字母与数字，最长 128 字符。

响应 `201`：

```json
{
  "id": "3f1b...",
  "email": "candidate@example.com",
  "email_verified": false,
  "created_at": "2026-10-26T05:00:00Z"
}
```

响应体不包含密码或其哈希。失败：`409 EMAIL_ALREADY_REGISTERED`、`422 VALIDATION_ERROR`。

---

## POST /api/v1/auth/login

请求体：

```json
{ "email": "candidate@example.com", "password": "Passw0rd1" }
```

响应 `200`：

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "Zm9vYmFy...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_expires_in": 2592000
}
```

同时下发 `refresh_token` 的 `httpOnly` Cookie。

失败：`401 INVALID_CREDENTIALS`（密码错误与账号不存在返回**完全相同**的响应，避免账号枚举）。

---

## POST /api/v1/auth/refresh

用刷新令牌换取新令牌对；每次调用都会轮换刷新令牌。

请求体（浏览器可省略，使用 Cookie）：

```json
{ "refresh_token": "Zm9vYmFy..." }
```

响应 `200`：同登录响应。

失败：

- `401 TOKEN_INVALID` —— 缺少刷新令牌，或找不到与之匹配的令牌。
- `401 TOKEN_EXPIRED` —— 刷新令牌已过期，需重新登录。
- `401 REFRESH_TOKEN_REUSED` —— 令牌已被使用或已被吊销（含登出后再次使用），
  该用户**全部**有效刷新令牌会被吊销，需重新登录。

---

## POST /api/v1/auth/logout

吊销当前刷新令牌并清除 Cookie。请求体可为 `{}`。

响应 `204`，无响应体。重复登出仍返回 `204`，不泄露令牌状态。

---

## GET /api/v1/users/me

获取当前登录用户信息，需 `Authorization: Bearer <access_token>`。

响应 `200`：

```json
{
  "id": "3f1b...",
  "email": "candidate@example.com",
  "email_verified": false,
  "created_at": "2026-10-26T05:00:00Z"
}
```

失败：`401 UNAUTHORIZED`（无令牌）、`401 TOKEN_INVALID` / `TOKEN_EXPIRED`（令牌无效或过期）。

---

## GET /api/v1/health

无需认证，用于探活。

响应 `200`：

```json
{ "status": "ok", "database": "ok", "trace_id": "9f2c1a..." }
```

数据库不可用时返回 `503`：`{"status": "degraded", "database": "unavailable", ...}`。

## 简历管理

所有端点需 `Authorization: Bearer <access_token>`。

### POST /api/v1/resumes

上传简历。multipart/form-data，字段 `file`。

- 仅接受 PDF / DOCX / TXT，单文件 ≤ 10MB。
- 上传成功返回 `201` 与简历对象；文件随后自动解析，结果通过 `parse_status` 体现。

响应 `201`：

```json
{
  "id": "0c9d...",
  "original_name": "我的简历.docx",
  "size_bytes": 24576,
  "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "parse_status": "succeeded",
  "parse_error": null,
  "parse_error_code": null,
  "created_at": "2026-10-26T07:00:00Z"
}
```

`parse_status`：

- `succeeded` —— 解析成功，文本已可用于押题。
- `failed` —— 解析失败，`parse_error` 为原因说明，`parse_error_code` 恒为 `PARSE_FAILED`。

错误响应：

| 状态码 | code | 场景 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带或无效访问令牌 |
| 413 | `FILE_TOO_LARGE` | 文件超过 10MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | 非 PDF/DOCX/TXT |
| 409 | `RESUME_QUOTA_EXCEEDED` | 达到每用户简历数量上限（默认 10 份） |

### GET /api/v1/resumes

返回本人简历列表，`200`，元素结构同上。仅返回本人简历。

### GET /api/v1/resumes/{resume_id}/preview

预览简历解析文本（属主隔离）。响应 `200`：

```json
{
  "id": "0c9d...",
  "original_name": "我的简历.docx",
  "parsed_text": "张三\n五年 Python 后端经验…"
}
```

| 状态码 | code | 场景 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带或无效访问令牌 |
| 404 | `NOT_FOUND` | 简历不存在或不属于当前用户 |
| 409 | `RESUME_NOT_PARSED` | 简历解析失败（message 为解析失败原因） |

### DELETE /api/v1/resumes/{resume_id}

彻底删除简历（记录、文件与解析结果）。返回 `204`。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 简历不存在或不属于当前用户（不区分这两种情况） |

## 知识库文档

所有端点需 `Authorization: Bearer <access_token>`。

### POST /api/v1/knowledge/documents

上传知识库文档。multipart/form-data：字段 `file`（PDF/DOCX/TXT/MD，≤10MB）与 `is_public`（默认 false）。

响应 `201`：

```json
{
  "id": "5f3a...",
  "name": "notes.md",
  "size_bytes": 1024,
  "content_type": "text/markdown",
  "is_public": false,
  "retrievable": true,
  "parse_error": null,
  "parse_error_code": null,
  "created_at": "2026-10-26T07:00:00Z"
}
```

- `retrievable=true`：文档已分块，可被押题检索引用。
- `retrievable=false`：无法提取有效文本，`parse_error` 说明原因，`parse_error_code` 为 `PARSE_FAILED`。

错误响应：`401 UNAUTHORIZED`、`413 FILE_TOO_LARGE`、`415 UNSUPPORTED_FILE_TYPE`。

### GET /api/v1/knowledge/documents

返回「公开文档 ∪ 本人上传的文档」，`200`。

### GET /api/v1/knowledge/documents/{document_id}

读取单个可见文档，`200`。他人的私有文档按不存在处理：返回 `404 NOT_FOUND`。

### DELETE /api/v1/knowledge/documents/{document_id}

删除本人上传的文档（记录、分片索引与文件）。返回 `204`。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 文档不存在 |
| 403 | `FORBIDDEN` | 尝试删除不属于自己的文档 |

## 押题生成

所有端点需 `Authorization: Bearer <access_token>`。押题由 AI 生成，响应中包含模型名称、提示词版本与生成时间。

### POST /api/v1/predictions

同步生成押题（模型调用可能持续数十秒）。请求体：

```json
{
  "resume_id": "0c9d...",
  "target_role": "Python 后端工程师",
  "years_of_experience": "3-5年",
  "job_description": "负责后端服务开发，使用 Python 与 FastAPI，熟悉数据库设计。（≤2000 字）",
  "programming_language": "Python"
}
```

`target_role`、`years_of_experience`、`job_description` 必填；`programming_language` 可选。

响应 `201`：

```json
{
  "id": "b21c...",
  "status": "completed",
  "target_role": "Python 后端工程师",
  "years_of_experience": "3-5年",
  "job_description": "...",
  "programming_language": "Python",
  "model_name": "deepseek-chat",
  "prompt_version": "prediction-v1",
  "generated_at": "2026-10-26T07:00:00Z",
  "questions": [
    {
      "position": 1,
      "question": "请介绍你在 FastAPI 项目中的经验",
      "difficulty": "medium",
      "reference_answer": "要点：项目背景、承担职责、遇到的问题与解决思路。",
      "evidence": [
        { "source": "resume", "ref": "我的简历.docx", "ref_id": null, "excerpt": "五年 Python 后端经验" },
        { "source": "knowledge", "ref": "tech.md", "ref_id": "5f3a...", "excerpt": "FastAPI 与数据库设计" }
      ]
    }
  ]
}
```

`evidence.source` 取值：`resume`（简历经历）/ `job_description`（岗位描述要求）/ `knowledge`（知识库文档，`ref_id` 为文档标识）。

错误响应：

| 状态码 | code | 场景 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带或无效访问令牌 |
| 422 | `VALIDATION_ERROR` | 字段缺失、岗位描述超 2000 字等（details 含字段级错误） |
| 404 | `NOT_FOUND` | 简历不存在或不属于当前用户 |
| 409 | `RESUME_NOT_PARSED` | 所选简历解析失败，不可用于押题 |
| 503 | `MODEL_UNAVAILABLE` | 未配置模型凭据或模型调用失败/超时 |
| 502 | `MODEL_OUTPUT_INVALID` | 模型返回内容无法构成押题列表 |

### GET /api/v1/predictions

返回本人押题历史（按生成时间倒序），`200`，元素含 `id、target_role、years_of_experience、model_name、prompt_version、generated_at、question_count`。

### GET /api/v1/predictions/{prediction_id}

返回单次押题明细（含目标信息快照、题目列表与生成元数据），`200`。他人的押题记录返回 `404 NOT_FOUND`。

## 字典（下拉选项配置）

维护押题向导中「目标岗位」「编程语言」的可选值。所有端点需 `Authorization: Bearer <access_token>`；登录用户可读、可管理。

支持的字典类型（`type`）：`target_role`（目标岗位）、`programming_language`（编程语言）。

### GET /api/v1/dictionaries

返回全部字典项，`200`（设置页管理用）。

### GET /api/v1/dictionaries/{type}

返回指定类型中已启用的选项（按排序权重），`200`。未知类型返回 `422 VALIDATION_ERROR`。

### POST /api/v1/dictionaries

新增字典项。请求体：

```json
{ "type": "target_role", "label": "Python 后端工程师", "value": "可选，缺省同 label" }
```

响应 `201` 与字典项对象。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带或无效访问令牌 |
| 409 | `DICT_ITEM_EXISTS` | 同类型下存储值重复 |
| 422 | `VALIDATION_ERROR` | 类型不在白名单、名称为空等 |

### DELETE /api/v1/dictionaries/{item_id}

删除字典项。返回 `204`；不存在返回 `404 NOT_FOUND`。

## 系统设置（LLM 凭据）

维护押题所用的大模型凭据（平台级，登录用户即可操作）。任何接口**不会返回完整的 API Key**，只返回 `***` + 末 4 位的脱敏掩码。凭据解析优先级：数据库覆盖 > 环境变量；保存后立即生效，无需重启。

### GET /api/v1/settings/llm

返回凭据状态：

```json
{
  "has_api_key": true,
  "api_key_masked": "***abcd",
  "base_url": "https://api.deepseek.com",
  "model": "deepseek-chat",
  "source": "database"
}
```

`source`：`database`（数据库覆盖）/ `environment`（环境变量）/ `none`（均未配置）。

### PUT /api/v1/settings/llm

更新凭据。请求体字段均可选：

| 字段 | 语义 |
| --- | --- |
| `api_key` | 缺省=不变；空串=清除（回落环境变量）；非空=更新 |
| `base_url` | 缺省=不变；空串=恢复服务端默认；必须以 http(s):// 开头 |
| `model` | 缺省=不变；空串=恢复服务端默认 |

响应 `200`：`{ has_api_key, api_key_masked, message }`。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 未携带或无效访问令牌 |
| 422 | `VALIDATION_ERROR` | Base URL 非 http(s) 格式等 |

## 面试会话

一问一答模拟面试：题目来自押题记录，问答全量落库，支持恢复。所有端点需 `Authorization: Bearer <access_token>`。

### POST /api/v1/interviews

基于押题记录发起面试。请求体：`{ "prediction_id": "..." }`。

响应 `201`：`{ interview: {..., messages: [...]}, questions: [{position, question, difficulty, reference_answer}] }`。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 押题不存在或不属于当前用户（引导先完成押题） |
| 409 | `INTERVIEW_ALREADY_ONGOING` | 该押题已有进行中的会话（引导恢复） |

### GET /api/v1/interviews

本人会话列表（倒序）：`[{ id, status, target_role, total_questions, current_position, started_at, finished_at, answered_count }]`。

### GET /api/v1/interviews/{interview_id}

会话详情：含 `messages`（`interviewer` 提问 / `answerer` 回答，`skipped` 标记跳过）与完整进度。他人会话返回 `404 NOT_FOUND`。

### POST /api/v1/interviews/{interview_id}/answer

提交当前题目回答。请求体：`{ "content": "回答内容（1-5000 字，纯空白拒绝）" }`。

响应 `200`：`{ interview, questions, finished }`——`finished=true` 表示最后一题已答完、会话完成。

| 状态码 | code | 场景 |
| --- | --- | --- |
| 409 | `INTERVIEW_NOT_ONGOING` | 会话已完成/放弃 |
| 422 | `VALIDATION_ERROR` | 回答为空或超长 |

### POST /api/v1/interviews/{interview_id}/skip

跳过当前题目：标记已跳过（无回答内容，不可撤销），推进到下一题；跳过末题同样完成会话。响应结构同上。

### POST /api/v1/interviews/{interview_id}/abandon

放弃进行中的会话。返回 `204`；放弃后不可再作答，可基于同一押题重新发起。
