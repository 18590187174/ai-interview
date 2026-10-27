# Tasks

> 图例：`- [x]` = 已完成（部分预览主题会将其渲染成叉，属显示差异），`- [ ]` = 未完成。

## 1. 配置与依赖

- [x] 1.1 后端新增依赖（python-multipart、pypdf、python-docx、langchain-core、langchain-openai），验证 `pip install -e ".[dev]"` 安装成功且核心模块可导入
- [x] 1.2 扩展配置模块：LLM 项（LLM_API_KEY 可选、LLM_BASE_URL、LLM_MODEL、LLM_TIMEOUT_SECONDS、LLM_TEMPERATURE、LLM_MAX_OUTPUT_TOKENS、PROMPT_VERSION、PREDICTION_QUESTION_COUNT）与上传项（UPLOAD_ROOT、UPLOAD_MAX_SIZE_MB、RESUME_QUOTA_PER_USER、RESUME_MAX_CHARS），验证未配置 Key 时应用可正常启动、配置测试通过

## 2. 存储与解析基础

- [x] 2.1 实现存储接口抽象与本地文件系统实现（save/read/delete，按属主与资源分目录），验证保存、读取、删除与越界路径拒绝的单元测试通过
- [x] 2.2 实现简历与文档解析器（PDF/DOCX/TXT/MD → 纯文本；损坏、加密、空内容分别映射为明确的解析失败原因），验证三种格式成功解析与三类失败场景的单元测试通过

## 3. 数据模型与迁移

- [x] 3.1 定义 resumes、knowledge_documents、knowledge_chunks、predictions、predicted_questions 五个模型（属主外键、解析状态、可见性、快照字段、命中依据 JSON），验证模型可建表且字段符合 design 第 6 条
- [x] 3.2 生成 Alembic 迁移并纳入迁移测试，验证 SQLite 上 upgrade 幂等、downgrade base 不残留新表、（可选）PostgreSQL 上 upgrade 成功

## 4. 简历管理 API

- [x] 4.1 实现简历上传端点（格式/体积校验、配额校验、存储、解析状态回填），验证合规上传 201、超限 413 `FILE_TOO_LARGE`、非法格式 415 `UNSUPPORTED_FILE_TYPE`、超配额 409 `RESUME_QUOTA_EXCEEDED` 的测试通过
- [x] 4.2 实现简历列表与删除端点（属主过滤、404 不泄露存在性、删除同时清理文件与解析结果），验证列表只含本人简历、他人标识返回 404、删除后文件不残留的测试通过
- [x] 4.3 在 `docs/api.md` 追加简历接口契约，验证按文档实测与行为一致
- [x] 4.4 实现简历解析文本预览端点 `GET /resumes/{id}/preview`（属主隔离、解析失败 409 `RESUME_NOT_PARSED`）并补测试，验证 spec 场景全部通过
- [x] 4.5 押题向导第二步增加「预览」入口（弹窗展示解析文本），并在 `docs/api.md` 补充预览契约，验证手动预览流程可用

## 5. 知识库 API

- [x] 5.1 实现文档上传与分块端点（格式/体积校验、分片入库、空文档标记不可检索），验证上传 201、分片数量正确、空文档标记与错误码的测试通过
- [x] 5.2 实现文档列表、删除与可见范围端点（公开 ∪ 本人、404/403 语义、删除清理分片与文件），验证可见范围、越权删除 403 `FORBIDDEN`、删除后分片不参与检索的测试通过
- [x] 5.3 实现关键词检索服务（按岗位描述与岗位名对片段打分取 Top-N，接口可替换），验证给定样例语料时相关片段排序靠前的单元测试通过

## 6. 押题服务与 API

- [x] 6.1 实现 LLM 服务封装（LangChain ChatOpenAI + Pydantic 结构化输出，未配置 Key 时明确报错），验证以桩替换 ChatOpenAI 时结构化解析、超时与异常路径的单元测试通过
- [x] 6.2 实现押题服务与端点（目标信息校验、简历状态检查 `RESUME_NOT_PARSED`、知识库检索注入、押题记录与题目落库、元数据返回、`MODEL_UNAVAILABLE`/`MODEL_OUTPUT_INVALID` 错误路径），验证 spec 中全部场景的测试通过
- [x] 6.3 在 `docs/api.md` 追加押题与知识库接口契约，验证按文档实测与行为一致
- [x] 6.4 押题输出新增参考答案：模型与 schema 增加 `reference_answer`（可空迁移）、提示词要求输出答题要点，并补测试，验证生成响应携带参考答案
- [x] 6.5 前端问题卡片增加参考答案收起/展开控件（默认收起、无该字段的历史记录不显示），题目列表区域增加滚动容器，验证交互与历史数据兼容

## 7. 前端：知识库页面

- [x] 7.1 实现知识库页面（Element Plus Upload 上传、文档列表、删除确认、公开标记展示），验证上传成功/失败提示、列表刷新与删除后消失的手动检查通过
- [x] 7.2 补充知识库 API 客户端与组件单元测试，验证 `npm run test` 全部通过

## 8. 前端：简历押题向导

- [x] 8.1 实现押题向导第一步（目标岗位、工作年限、岗位描述字数限制 2000、编程语言可选，字段级校验与错误提示），验证非法提交被拦截且提示与后端 422 明细一致
- [x] 8.2 实现第二步（已有简历列表选择或新上传，上传进度与失败提示），验证选择解析失败简历时的提示与禁用状态正确
- [x] 8.3 实现第三步（AI 分析中 loading、押题列表展示：题目、难度、命中依据、来源文档、生成元数据与 AI 生成标注），验证端到端生成后页面完整渲染
- [x] 8.4 补充押题向导的 API 客户端与组件单元测试，验证 `npm run test` 全部通过

## 9. 集成验证

- [ ] 9.1 以真实 PostgreSQL 环境端到端跑通「上传简历 → 上传知识库文档 → 填写目标信息 → 生成押题 → 查看命中依据与元数据 → 删除简历/文档 → 再次押题被拦截」，验证全流程行为与三个 delta spec 场景一致
- [x] 9.2 运行 `openspec validate resume-question-prediction --strict`，验证三个 delta spec 全部通过校验

## Workflow follow-up

- 评审通过后执行 `/opsx:archive`，将 delta 合并进 `openspec/specs/` 并把变更目录移入 `openspec/changes/archive/`。
