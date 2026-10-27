"""大模型服务封装：OpenAI 兼容接口 + Pydantic 结构化输出。

业务层只依赖 LLMClient 抽象，测试可注入桩实现。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.services.system_settings import LLMRuntimeConfig

logger = logging.getLogger(__name__)

EVIDENCE_SOURCES = {"resume", "job_description", "knowledge"}


class Evidence(BaseModel):
    """单条命中依据。"""

    source: str = Field(description="来源类型：resume / job_description / knowledge")
    ref: str = Field(description="来源名称：简历文件名 / 岗位描述 / 知识库文档名")
    excerpt: str = Field(description="支持该题目的关键引用")


class PredictedQuestionDraft(BaseModel):
    """大模型输出的单道押题。"""

    question: str = Field(description="押题题目")
    difficulty: str = Field(description="难度：easy / medium / hard")
    reference_answer: str = Field(description="简要参考答案（答题要点，3-6 句）")
    evidence: list[Evidence] = Field(default_factory=list, description="命中依据")


class PredictionDraft(BaseModel):
    """大模型输出的押题列表。"""

    questions: list[PredictedQuestionDraft] = Field(description="押题列表，按可能性从高到低")


class LLMClient(ABC):
    """大模型客户端抽象。"""

    @abstractmethod
    def generate_prediction(
        self,
        *,
        settings: Settings,
        config: LLMRuntimeConfig,
        target_role: str,
        years_of_experience: str,
        job_description: str,
        programming_language: str | None,
        resume_text: str,
        knowledge_snippets: list[str],
        question_count: int,
    ) -> PredictionDraft:
        """生成押题草稿；不可用时抛出 AppError。"""


def build_prompt(
    *,
    target_role: str,
    years_of_experience: str,
    job_description: str,
    programming_language: str | None,
    resume_text: str,
    knowledge_snippets: list[str],
    question_count: int,
    max_resume_chars: int,
) -> str:
    truncated = resume_text[:max_resume_chars]
    notice = "\n（简历内容过长，以下为节选）" if len(resume_text) > max_resume_chars else ""
    references = (
        "\n".join(f"- {snippet}" for snippet in knowledge_snippets)
        if knowledge_snippets
        else "（本次未提供知识库资料）"
    )
    return (
        "你是一名资深技术面试官。请基于以下材料，生成 "
        f"{question_count} 道最可能被问到的面试题。\n\n"
        f"【目标岗位】{target_role}\n"
        f"【工作年限】{years_of_experience}\n"
        f"【岗位描述】{job_description}\n"
        f"【编程语言】{programming_language or '未指定'}\n\n"
        f"【简历内容】{notice}\n{truncated}\n\n"
        f"【参考资料片段】\n{references}\n\n"
        "要求：\n"
        "1. 只输出最可能被问到的题目，按可能性从高到低排序。\n"
        "2. 每道题必须给出命中依据：source 取 resume / job_description / knowledge 之一；"
        "ref 填写来源名称（简历文件名、『岗位描述』或知识库文档名）；excerpt 给出关键引用。\n"
        "3. difficulty 取值：easy / medium / hard。\n"
        "4. 每道题给出简要参考答案（答题要点，3-6 句，围绕该题的考察点与作答思路）。\n"
    )


class OpenAICompatLLM(LLMClient):
    """OpenAI 兼容接口实现（默认 DeepSeek）。"""

    def generate_prediction(
        self,
        *,
        settings: Settings,
        config: LLMRuntimeConfig,
        target_role: str,
        years_of_experience: str,
        job_description: str,
        programming_language: str | None,
        resume_text: str,
        knowledge_snippets: list[str],
        question_count: int,
    ) -> PredictionDraft:
        if not config.api_key:
            raise AppError(
                503,
                ErrorCode.MODEL_UNAVAILABLE,
                "未配置大模型访问凭据，请前往「设置」页填写 API Key 后重试",
            )

        from langchain_openai import ChatOpenAI  # 延迟导入，加快应用启动

        llm = ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_output_tokens,
        )
        prompt = build_prompt(
            target_role=target_role,
            years_of_experience=years_of_experience,
            job_description=job_description,
            programming_language=programming_language,
            resume_text=resume_text,
            knowledge_snippets=knowledge_snippets,
            question_count=question_count,
            max_resume_chars=settings.resume_max_chars,
        )

        try:
            # DeepSeek 不支持 json_schema response_format，改用 function calling 约束输出
            structured = llm.with_structured_output(PredictionDraft, method="function_calling")
            draft = structured.invoke(prompt)
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001 - 统一归一为模型不可用，不泄露内部细节
            logger.warning("大模型调用失败", exc_info=True)
            raise AppError(
                503, ErrorCode.MODEL_UNAVAILABLE, "大模型服务暂不可用，请稍后重试"
            ) from exc

        if not draft or not draft.questions:
            raise AppError(502, ErrorCode.MODEL_OUTPUT_INVALID, "大模型返回内容无效，请重试")
        return draft
