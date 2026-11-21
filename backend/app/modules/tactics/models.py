from __future__ import annotations

from datetime import datetime
from enum import Enum as PythonEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.auth.models import User
from app.shared.database import Base


class Formation(str, PythonEnum):
    FOUR_THREE_THREE = "4-3-3"
    FOUR_TWO_THREE_ONE = "4-2-3-1"
    FOUR_FOUR_TWO = "4-4-2"
    THREE_FOUR_THREE = "3-4-3"
    THREE_FIVE_TWO = "3-5-2"
    FIVE_THREE_TWO = "5-3-2"


class PlayingStyle(str, PythonEnum):
    POSSESSION = "possession"
    COUNTER_ATTACK = "counter_attack"
    HIGH_PRESS = "high_press"
    LOW_BLOCK = "low_block"
    WING_PLAY = "wing_play"
    DIRECT = "direct"
    BALANCED = "balanced"


class TeamTactic(Base):
    __tablename__ = "team_tactics"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    formation: Mapped[Formation] = mapped_column(
        Enum(Formation, name="formation", values_callable=lambda values: [value.value for value in values]),
        nullable=False,
    )
    playing_style: Mapped[PlayingStyle] = mapped_column(
        Enum(PlayingStyle, name="playing_style", values_callable=lambda values: [value.value for value in values]),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    updated_by: Mapped[User | None] = relationship(lazy="joined")
