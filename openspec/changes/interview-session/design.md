# Design

## Context

押题能力已上线（押题记录含题目列表），主线需要把押题产物变为可练习的面试。语音作答在 config.yaml 约束中要求 ASR 失败可回退打字；长流程交互要求会话状态持久化。

## Goals / Non-Goals

Goals:

- 从押题记录到一问一答面试的最小完整闭环：发起 → 逐题作答 → 完成
- 会话与消息全量持久化，断线可恢复
- 语音输入零后端成本（浏览器端识别），失败自动回退

Non-Goals（已确认排期后续变更）:

- **AI 动态追问**：已确认作为后续变更——基于本会话落库的完整问答数据，由 AI 针对回答生成追问，届时以独立 change 提案
- **面试评分报告**（`interview-report`）：消费本能力积累的问答数据
- 音频存储与服务端 ASR
- 实时流式输出（题目是确定性的，无需流式）

## Decisions

### 1. 题目来源：直接复用押题题目列表，不调用大模型

面试题目 = 所选押题记录的题目顺序列表。推进逻辑是确定性的（回答 → 存库 → 下一题），提交回答不调用 LLM：

- 优点：响应快（毫秒级）、无 token 成本、断线恢复与进度推进绝对可靠
- 代价：面试官不追问、不改写问题——「动态追问」作为 `interview-report` 之后的增强（需要时以新变更引入，spec 层面留有空间：本题要求"逐题提出"，未约束提问者必须是人、是 AI 还是模板）

### 2. 数据模型：会话 + 消息两张表

- `interviews`：属主、`prediction_id`（外键）、状态（`ongoing` / `completed` / `abandoned`）、题目总数、当前题号 `current_position`、快照字段（岗位/年限/描述）、开始与完成时间
- `interview_messages`：会话外键、角色（`interviewer` 提问 / `answerer` 回答）、题号、内容、时间戳——问答交替成对存储

进度推进：提交回答时写入 answerer 消息；若还有下一题，同时写入下一条 interviewer 消息并把 `current_position` 前移；最后一题后置状态 `completed`。恢复 = 按 `current_position` 取当前 interviewer 消息渲染。

### 3. 同一会话约束与重复发起

同一 `prediction_id` 存在 `ongoing` 会话时拒绝再发起（409 `INTERVIEW_ALREADY_ONGOING`），引导用户恢复——避免题目推进状态分裂。放弃会话后可重新发起。

### 4. 语音：浏览器 Web Speech API，零后端

语音识别在浏览器端完成（`webkitSpeechRecognition`，Chrome/Edge 支持 zh-CN），转写文本填入输入框，用户确认后与打字作答同路提交。不支持的环境（Firefox/Safari 部分、无麦克风权限）直接不渲染语音按钮。后端不感知语音的存在——回答永远是文本，因此无音频存储、无 ASR 服务依赖，天然满足「识别失败回退打字」与「不产生音频存储」。

备选：服务端 ASR（Whisper 兼容接口）。拒绝理由：引入音频上传/存储/清理成本与第三方依赖，浏览器方案已覆盖主流环境。

### 5. 会话完成即锁死

`completed` / `abandoned` 的会话拒绝回答（409 `INTERVIEW_NOT_ONGOING`）。报告能力将消费这些只读数据。

## Risks / Trade-offs

- [AI 不追问，面试真实感有限] → 确定题目 + 顺利推进是评分报告的可靠数据基础；追问作为增强后续引入
- [押题题目质量直接决定面试体验] → 押题侧已有命中依据与提示词约束；可在发起时展示题目预览
- [Web Speech API 依赖浏览器与网络（Chrome 用谷歌服务）] → 回退路径明确（打字），语音入口按能力探测渲染
- [长回答丢失风险] → 作答提交成功前不推进题号；前端输入框内容在组件内保留（KeepAlive），提交失败不清空

## Migration Plan

1. 新增迁移（两张表），upgrade/downgrade 双向验证
2. 全部新端点在 `/api/v1/interviews` 下，受认证保护（沿用默认拒绝）
3. 回滚：downgrade 移除表；面试功能为增量，不影响存量押题数据

## Open Questions

（评审已拍板：支持跳过本题；语音转写为手动确认提交。暂无待定项。）
