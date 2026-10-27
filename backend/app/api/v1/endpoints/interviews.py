"""面试会话端点。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.interview import (
    AnswerCreate,
    AnswerResultOut,
    InterviewCreate,
    InterviewOut,
    InterviewStartOut,
    InterviewSummaryOut,
)
from app.services import interview as interview_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InterviewStartOut)
def start_interview(
    payload: InterviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewStartOut:
    return interview_service.start_interview(db, user=user, prediction_id=payload.prediction_id)


@router.get("", response_model=list[InterviewSummaryOut])
def list_interviews(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InterviewSummaryOut]:
    return [
        InterviewSummaryOut(
            id=interview.id,
            status=interview.status,
            target_role=interview.target_role,
            total_questions=interview.total_questions,
            current_position=interview.current_position,
            started_at=interview.created_at,
            finished_at=interview.finished_at,
            answered_count=answered,
        )
        for interview, answered in interview_service.list_interviews(db, user.id)
    ]


@router.get("/{interview_id}", response_model=InterviewOut)
def get_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewOut:
    interview = interview_service.get_owned_interview(db, user.id, interview_id)
    return InterviewOut.model_validate(interview)


@router.post("/{interview_id}/answer", response_model=AnswerResultOut)
def submit_answer(
    interview_id: uuid.UUID,
    payload: AnswerCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnswerResultOut:
    interview, questions, finished = interview_service.submit_answer(
        db, owner_id=user.id, interview_id=interview_id, content=payload.content
    )
    return AnswerResultOut(
        interview=interview,
        questions=questions,
        finished=finished,
    )


@router.post("/{interview_id}/skip", response_model=AnswerResultOut)
def skip_question(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnswerResultOut:
    interview, questions, finished = interview_service.skip_question(
        db, owner_id=user.id, interview_id=interview_id
    )
    return AnswerResultOut(
        interview=interview,
        questions=questions,
        finished=finished,
    )


@router.post("/{interview_id}/abandon", status_code=status.HTTP_204_NO_CONTENT)
def abandon_interview(
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    interview_service.abandon_interview(db, owner_id=user.id, interview_id=interview_id)
