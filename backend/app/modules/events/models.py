from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum as PythonEnum

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.auth.models import User
from app.modules.players.models import Player
from app.shared.database import Base


class TeamEventType(str, PythonEnum):
    MEDICAL = "medical"
    TRAINING = "training"
    DRESSING_ROOM = "dressing_room"


class TeamEvent(Base):
    __tablename__ = "team_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[TeamEventType] = mapped_column(
        Enum(
            TeamEventType,
            name="team_event_type",
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
        index=True,
    )
    player_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), ForeignKey("players.player_id")
    )
    injury_date: Mapped[date | None] = mapped_column(Date)
    event_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    recovery_days: Mapped[int | None] = mapped_column(Integer)
    training_project: Mapped[str | None] = mapped_column(String(200))
    training_effect: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    player: Mapped[Player | None] = relationship(lazy="joined")
    created_by: Mapped[User | None] = relationship(lazy="joined")

    @property
    def expected_return_date(self) -> date | None:
        if self.injury_date is None or self.recovery_days is None:
            return None
        return self.injury_date + timedelta(days=self.recovery_days)
