"""押题生成业务逻辑：校验、检索注入、大模型调用与结果落库。"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.models.prediction import PredictedQuestion, Prediction
from app.models.user import User
from app.services.knowledge import retrieve_chunks
from app.services.llm import LLMClient
from app.services.resume import get_owned_resume
from app.services.system_settings import effective_llm_config

logger = logging.getLogger(__name__)


def _validate_evidence_sources(
    prediction: Prediction,
    used_documents: dict[str, uuid.UUID],
) -> None:
    """把知识库来源的 ref（文档名）回填为文档标识，便于追溯。"""
    for question in prediction.questions:
        for evidence in question.evidence:
            if evidence.get("source") == "knowledge" and evidence.get("ref") in used_documents:
                evidence["ref_id"] = str(used_documents[evidence["ref"]])


def create_prediction(
    db: Session,
    *,
    user: User,
    resume_id: uuid.UUID,
    target_role: str,
    years_of_experience: str,
    job_description: str,
    programming_language: str | None,
    settings: Settings,
    llm: LLMClient,
) -> Prediction:
    resume = get_owned_resume(db, user.id, resume_id)
    if resume.parse_status != "succeeded":
        raise AppError(
            409,
            ErrorCode.RESUME_NOT_PARSED,
            "简历尚未成功解析，无法用于押题，请更换文件或重新上传",
        )

    matched = retrieve_chunks(
        db,
        user=user,
        target_role=target_role,
        job_description=job_description,
    )
    knowledge_snippets = [
        f"《{document.name}》：{chunk.content.strip()}" for chunk, document in matched
    ]
    used_documents = {document.name: document.id for _, document in matched}

    try:
        draft = llm.generate_prediction(
            settings=settings,
            config=effective_llm_config(db, settings),
            target_role=target_role,
            years_of_experience=years_of_experience,
            job_description=job_description,
            programming_language=programming_language,
            resume_text=resume.parsed_text or "",
            knowledge_snippets=knowledge_snippets,
            question_count=settings.prediction_question_count,
        )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 - 客户端异常统一归一为模型不可用
        logger.warning("大模型调用失败", exc_info=True)
        raise AppError(503, ErrorCode.MODEL_UNAVAILABLE, "大模型服务暂不可用，请稍后重试") from exc

    if not draft.questions:
        raise AppError(502, ErrorCode.MODEL_OUTPUT_INVALID, "大模型返回内容无效，请重试")

    prediction = Prediction(
        owner_id=user.id,
        resume_id=resume.id,
        target_role=target_role,
        years_of_experience=years_of_experience,
        job_description=job_description,
        programming_language=programming_language,
        status="completed",
        model_name=settings.llm_model,
        prompt_version=settings.prompt_version,
        generated_at=datetime.now(UTC),
        questions=[],
    )
    for position, item in enumerate(draft.questions, start=1):
        evidence = [item_ev.model_dump() for item_ev in item.evidence]
        question = PredictedQuestion(
            prediction=prediction,
            position=position,
            question=item.question,
            difficulty=item.difficulty,
            reference_answer=item.reference_answer,
            evidence=evidence,
        )
        prediction.questions.append(question)

    _validate_evidence_sources(prediction, used_documents)

    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def list_predictions(db: Session, owner_id: uuid.UUID) -> list[Prediction]:
    return (
        db.query(Prediction)
        .filter(Prediction.owner_id == owner_id)
        .order_by(Prediction.generated_at.desc())
        .all()
    )


def get_owned_prediction(db: Session, owner_id: uuid.UUID, prediction_id: uuid.UUID) -> Prediction:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    # 属主隔离：他人资源一律按不存在处理
    if prediction is None or prediction.owner_id != owner_id:
        raise AppError(404, ErrorCode.NOT_FOUND, "押题记录不存在")
    return prediction
