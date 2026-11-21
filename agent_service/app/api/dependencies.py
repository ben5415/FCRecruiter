"""来自业务 Backend 的服务间认证。"""

from dataclasses import dataclass
from typing import Annotated
import hmac

from fastapi import Depends, Header, HTTPException, status

from agent_service.app.config import get_agent_settings


async def require_service_token(
    supplied: Annotated[str | None, Header(alias="X-Agent-Service-Token")] = None,
) -> None:
    expected = get_agent_settings().agent_service_token
    if not expected:
        raise HTTPException(status_code=503, detail="Service authentication is not configured")
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")


@dataclass(frozen=True)
class CallerIdentity:
    tenant_id: int
    user_id: int


async def require_caller_identity(
    _: Annotated[None, Depends(require_service_token)],
    tenant_id: Annotated[int, Header(alias="X-Tenant-ID")],
    user_id: Annotated[int, Header(alias="X-User-ID")],
) -> CallerIdentity:
    return CallerIdentity(tenant_id=tenant_id, user_id=user_id)
