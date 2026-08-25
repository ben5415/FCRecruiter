from fastapi import HTTPException, status

from app.modules.auth.models import User, UserRole
from app.modules.events.models import TeamEventType


WRITE_ROLES = {
    TeamEventType.MEDICAL: {UserRole.DOCTOR, UserRole.MANAGER},
    TeamEventType.TRAINING: {UserRole.COACH, UserRole.MANAGER},
    TeamEventType.DRESSING_ROOM: {UserRole.PLAYER, UserRole.COACH, UserRole.MANAGER},
}


def require_write_permission(user: User, event_type: TeamEventType) -> None:
    if user.role not in WRITE_ROLES[event_type]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {user.role.value} cannot write {event_type.value} events",
        )


def validate_event_fields(event_type: TeamEventType, values: dict[str, object]) -> None:
    required = {
        TeamEventType.MEDICAL: {"player_id", "injury_date", "description", "recovery_days"},
        TeamEventType.TRAINING: {"player_id", "event_date", "training_project", "training_effect"},
        TeamEventType.DRESSING_ROOM: {"event_date", "description"},
    }[event_type]
    allowed = required
    missing = [field for field in required if values.get(field) is None or values.get(field) == ""]
    unexpected = [field for field, value in values.items() if field not in allowed and value is not None]
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if unexpected:
            details.append(f"not allowed: {', '.join(sorted(unexpected))}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {event_type.value} event fields ({'; '.join(details)})",
        )
