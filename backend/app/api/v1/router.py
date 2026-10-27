"""API v1 路由聚合：公共路由与受保护路由分离，受保护路由默认要求有效访问令牌。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import (
    auth,
    dictionaries,
    health,
    interviews,
    knowledge,
    predictions,
    resumes,
    system_settings,
    users,
)

# 无需认证的路由：健康检查与认证入口
public_router = APIRouter()
public_router.include_router(health.router)
public_router.include_router(auth.router)

# 其余路由默认拒绝未认证访问
protected_router = APIRouter(dependencies=[Depends(get_current_user)])
protected_router.include_router(users.router)
protected_router.include_router(resumes.router)
protected_router.include_router(knowledge.router)
protected_router.include_router(predictions.router)
protected_router.include_router(dictionaries.router)
protected_router.include_router(interviews.router)
protected_router.include_router(system_settings.router)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(public_router)
api_router.include_router(protected_router)
