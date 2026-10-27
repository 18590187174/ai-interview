# Proposal

## Why

平台骨架、认证与统一导航已落地，但主线的第一个环节尚不可用：用户既不能上传简历、也无法描述目标岗位，因而拿不到针对性的押题列表；没有押题结果，后续的「开始面试」也没有题目可问。本次变更补齐「简历押题」的最小闭环，让用户第一次获得产品承诺的核心价值。

## What Changes

- 新增简历管理能力：上传（限定 PDF / DOCX / TXT，单文件 ≤ 10MB）、持久化存储、解析为纯文本、列表查看、选择用于押题、彻底删除（含文件与解析结果）
- 新增面试目标信息填写：目标岗位、工作年限、岗位描述（上限 2000 字）、编程语言（可选）
- 新增知识库最小可用能力：上传文档（同样限定格式与大小）、列表、删除；押题时作为 AI 分析的参考资料，并在结果中标注被引用的具体文档
- 新增押题生成能力：将「简历解析结果 + 目标岗位信息 + 命中的知识库片段」提交给大模型（LangChain 编排，OpenAI 兼容接口，默认 DeepSeek），输出最可能被问到的押题列表；每道题附**命中依据**（来自简历的哪段经历 / 岗位描述的哪条要求 / 知识库的哪份资料）
- 押题结果可追溯：记录模型名称、提示词版本与生成时间，界面标明由 AI 生成
- 前端「简历押题」由占位页改为可用向导（填写目标信息 → 选择或上传简历 → 押题列表），「知识库」由占位页改为上传与列表管理

明确排除（后续变更）：一问一答面试会话、面试评分与参考答案报告、「我的」页面中的历史回看。

## Capabilities

### New Capabilities

- `resume-management`：简历上传、存储、解析与选择，含访问控制与彻底删除
- `knowledge-base`：知识库文档管理，支持外部上传并对 AI 押题分析可见，检索结果可追溯到具体文档
- `question-prediction`：押题生成（简历解析结果 + 岗位描述 + 知识库片段 → AI 分析 → 押题列表与命中依据）

### Modified Capabilities

无。`app-shell` 在上一变更中已明确「开始面试」「简历押题」「知识库」为占位页面，且原文写明「后续变更逐个替换为真实功能」——本次替换属于该预留演进，不构成需求层面的行为变更，因此不产生 delta。

## Impact

- 后端：新增 `resumes`、`knowledge_documents`、`predictions`、`predicted_questions` 四张表与对应迁移；新增 `resumes`、`knowledge`、`predictions` 三组 `/api/v1` 端点；新增文件存储抽象、简历解析服务、知识库分块与检索服务、LLM 服务（LangChain + OpenAI 兼容接口）
- 配置：`app/core/config.py` 新增 LLM 相关项（API Key、Base URL、模型名、超时、温度、提示词版本）与上传限制项（文件类型、大小上限、存储根目录、单用户配额）
- 新增依赖：`python-multipart`、`pypdf`、`python-docx`、`langchain-core`、`langchain-openai`
- 前端：`src/views/ResumeQuizView.vue`、`src/views/KnowledgeView.vue` 由占位改造，`src/api/` 与 `src/stores/` 新增对应模块
- 外部依赖：需配置 DeepSeek API Key；缺少或调用失败时，押题接口 SHALL 返回明确的结构化错误（沿用统一错误格式），不得静默返回空列表
