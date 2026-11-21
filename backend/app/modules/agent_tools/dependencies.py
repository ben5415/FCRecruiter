"""服务间认证与 Agent Tool 执行身份解析。

Agent Service 传来的 tenant_id 和 user_id 都只是声明。Backend 必须用自己的
数据库重新查找用户、核对租户和角色，不能信任模型或上游服务传入的 role。
"""

from dataclasses import dataclass
from typing import Annotated
import hmac

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.modules.auth.models import User, UserRole
from app.shared.database import get_db_session


AGENT_TOOL_READ_ROLES = frozenset(UserRole)


@dataclass(frozen=True)
class AgentServicePrincipal:
    """Backend 验证后的真实执行身份。"""

    user: User

    @property
    def tenant_id(self) -> int:
        return self.user.tenant_id


async def require_agent_service_principal(
    db: Annotated[Session, Depends(get_db_session)],
    service_token: Annotated[str | None, Header(alias="X-Agent-Service-Token")] = None,
    tenant_id: Annotated[int | None, Header(alias="X-Tenant-ID")] = None,
    user_id: Annotated[int | None, Header(alias="X-User-ID")] = None,
) -> AgentServicePrincipal:
    """认证 Agent Service，并在 Backend 内重建可信用户身份。"""

    expected_token = get_settings().agent_service_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service integration is not configured",
        )
    if not service_token or not hmac.compare_digest(service_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")
    if tenant_id is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant and user identity headers are required",
        )

    user = db.scalar(
        select(User)
        .options(joinedload(User.tenant))
        .where(User.id == user_id, User.tenant_id == tenant_id)
    )
    if user is None or not user.is_active or not user.tenant.is_active:
        # 对跨租户 user_id/tenant_id 组合也返回 403，不泄露用户是否存在。
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent access denied")
    if user.role not in AGENT_TOOL_READ_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot use agent tools")
    return AgentServicePrincipal(user=user)
