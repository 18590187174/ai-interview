"""面试会话业务逻辑：发起、作答、跳过、恢复、放弃。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.interview import Interview, InterviewMessage
from app.models.prediction import PredictedQuestion, Prediction
from app.models.user import User
from app.schemas.interview import InterviewStartOut


def _questions_of(prediction: Prediction) -> list[PredictedQuestion]:
    return sorted(prediction.questions, key=lambda q: q.position)


def _questions_out(prediction: Prediction) -> list[dict]:
    return [
        {
            "position": q.position,
            "question": q.question,
            "difficulty": q.difficulty,
            "reference_answer": q.reference_answer,
        }
        for q in _questions_of(prediction)
    ]


def start_interview(db: Session, *, user: User, prediction_id: uuid.UUID) -> InterviewStartOut:
    prediction = (
        db.query(Prediction).filter(Prediction.id == prediction_id).first()
    )
    # 属主隔离：他人押题按不存在处理
    if prediction is None or prediction.owner_id != user.id:
        raise AppError(404, ErrorCode.NOT_FOUND, "押题记录不存在，请先完成简历押题")

    questions = _questions_of(prediction)
    if not questions:
        raise AppError(409, ErrorCode.VALIDATION_ERROR, "该押题记录没有题目，无法发起面试")

    ongoing = (
        db.query(Interview)
        .filter(
            Interview.prediction_id == prediction_id,
            Interview.status == "ongoing",
        )
        .first()
    )
    if ongoing is not None:
        raise AppError(
            409,
            ErrorCode.INTERVIEW_ALREADY_ONGOING,
            "该押题已有进行中的面试，请先恢复完成它",
        )

    interview = Interview(
        owner_id=user.id,
        prediction_id=prediction.id,
        status="ongoing",
        total_questions=len(questions),
        current_position=questions[0].position,
        target_role=prediction.target_role,
        years_of_experience=prediction.years_of_experience,
        job_description=prediction.job_description,
        programming_language=prediction.programming_language,
        messages=[
            InterviewMessage(
                role="interviewer",
                position=questions[0].position,
                content=questions[0].question,
            )
        ],
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return InterviewStartOut(
        interview=interview,
        questions=_questions_out(prediction),
    )


def get_owned_interview(db: Session, owner_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if interview is None or interview.owner_id != owner_id:
        raise AppError(404, ErrorCode.NOT_FOUND, "面试会话不存在")
    return interview


def _require_ongoing(interview: Interview) -> None:
    if interview.status != "ongoing":
        raise AppError(409, ErrorCode.INTERVIEW_NOT_ONGOING, "面试已结束，不能再作答")


def _prediction_of(db: Session, interview: Interview) -> Prediction:
    prediction = db.query(Prediction).filter(Prediction.id == interview.prediction_id).first()
    if prediction is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "面试关联的押题记录不存在")
    return prediction


def submit_answer(
    db: Session, *, owner_id: uuid.UUID, interview_id: uuid.UUID, content: str
) -> tuple[Interview, list[dict], bool]:
    interview = get_owned_interview(db, owner_id, interview_id)
    _require_ongoing(interview)
    prediction = _prediction_of(db, interview)
    questions = _questions_of(prediction)
    current = next((q for q in questions if q.position == interview.current_position), None)
    if current is None:
        raise AppError(409, ErrorCode.INTERVIEW_NOT_ONGOING, "当前题目不存在")

    db.add(
        InterviewMessage(
            interview_id=interview.id,
            role="answerer",
            position=current.position,
            content=content.strip(),
            skipped=False,
        )
    )
    return _advance(db, interview, questions)


def skip_question(
    db: Session, *, owner_id: uuid.UUID, interview_id: uuid.UUID
) -> tuple[Interview, list[dict], bool]:
    interview = get_owned_interview(db, owner_id, interview_id)
    _require_ongoing(interview)
    prediction = _prediction_of(db, interview)
    questions = _questions_of(prediction)
    current = next((q for q in questions if q.position == interview.current_position), None)
    if current is None:
        raise AppError(409, ErrorCode.INTERVIEW_NOT_ONGOING, "当前题目不存在")

    # 跳过：记录空回答并标记，不可撤销
    db.add(
        InterviewMessage(
            interview_id=interview.id,
            role="answerer",
            position=current.position,
            content=None,
            skipped=True,
        )
    )
    return _advance(db, interview, questions)


def _advance(
    db: Session, interview: Interview, questions: list[PredictedQuestion]
) -> tuple[Interview, list[dict], bool]:
    """题号推进：写入下一题的面试官消息；末题则完成会话。"""
    index = next(i for i, q in enumerate(questions) if q.position == interview.current_position)
    next_question = questions[index + 1] if index + 1 < len(questions) else None

    if next_question is None:
        interview.status = "completed"
        interview.finished_at = datetime.now(UTC)
    else:
        interview.current_position = next_question.position
        db.add(
            InterviewMessage(
                interview_id=interview.id,
                role="interviewer",
                position=next_question.position,
                content=next_question.question,
            )
        )

    db.commit()
    db.refresh(interview)
    question_dicts = [
        {
            "position": q.position,
            "question": q.question,
            "difficulty": q.difficulty,
            "reference_answer": q.reference_answer,
        }
        for q in questions
    ]
    return interview, question_dicts, next_question is None


def list_interviews(db: Session, owner_id: uuid.UUID) -> list[tuple[Interview, int]]:
    interviews = (
        db.query(Interview)
        .filter(Interview.owner_id == owner_id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    result: list[tuple[Interview, int]] = []
    for interview in interviews:
        answered = (
            db.query(InterviewMessage)
            .filter(
                InterviewMessage.interview_id == interview.id,
                InterviewMessage.role == "answerer",
            )
            .count()
        )
        result.append((interview, answered))
    return result


def abandon_interview(db: Session, *, owner_id: uuid.UUID, interview_id: uuid.UUID) -> None:
    interview = get_owned_interview(db, owner_id, interview_id)
    _require_ongoing(interview)
    interview.status = "abandoned"
    interview.finished_at = datetime.now(UTC)
    db.commit()
