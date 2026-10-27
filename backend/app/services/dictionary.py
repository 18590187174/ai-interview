"""字典管理业务逻辑：按类型读取、新增与删除。"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.dict_item import DictItem
from app.schemas.dictionary import DictItemCreate

# 允许配置的字典类型白名单
DICT_TYPES = {"target_role": "目标岗位", "programming_language": "编程语言"}


def validate_type(dict_type: str) -> str:
    if dict_type not in DICT_TYPES:
        raise AppError(
            422,
            ErrorCode.VALIDATION_ERROR,
            f"不支持的字典类型，允许的类型：{', '.join(sorted(DICT_TYPES))}",
        )
    return dict_type


def list_by_type(db: Session, dict_type: str) -> list[DictItem]:
    return (
        db.query(DictItem)
        .filter(DictItem.type == dict_type, DictItem.enabled.is_(True))
        .order_by(DictItem.sort_order, DictItem.created_at)
        .all()
    )


def list_all(db: Session) -> list[DictItem]:
    return db.query(DictItem).order_by(DictItem.type, DictItem.sort_order).all()


def create_item(db: Session, payload: DictItemCreate) -> DictItem:
    validate_type(payload.type)
    label = payload.label.strip()
    if not label:
        raise AppError(422, ErrorCode.VALIDATION_ERROR, "字典项名称不能为空")

    value = (payload.value or label).strip()
    exists = (
        db.query(DictItem)
        .filter(DictItem.type == payload.type, DictItem.value == value)
        .first()
    )
    if exists is not None:
        raise AppError(409, ErrorCode.DICT_ITEM_EXISTS, f"字典项「{label}」已存在")

    item = DictItem(
        type=payload.type,
        label=label,
        value=value,
        sort_order=payload.sort_order,
        enabled=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: uuid.UUID) -> None:
    item = db.query(DictItem).filter(DictItem.id == item_id).first()
    if item is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "字典项不存在")
    db.delete(item)
    db.commit()
