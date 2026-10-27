"""字典端点：登录用户可读、可管理。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.dictionary import DictItemCreate, DictItemOut
from app.services import dictionary as dictionary_service

router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])


@router.get("", response_model=list[DictItemOut])
def list_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DictItemOut]:
    items = dictionary_service.list_all(db)
    return [DictItemOut.model_validate(item) for item in items]


@router.get("/{dict_type}", response_model=list[DictItemOut])
def list_by_type(
    dict_type: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DictItemOut]:
    dictionary_service.validate_type(dict_type)
    items = dictionary_service.list_by_type(db, dict_type)
    return [DictItemOut.model_validate(item) for item in items]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DictItemOut)
def create_item(
    payload: DictItemCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DictItemOut:
    item = dictionary_service.create_item(db, payload)
    return DictItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    dictionary_service.delete_item(db, item_id)
