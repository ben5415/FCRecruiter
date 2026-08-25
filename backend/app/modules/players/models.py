from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class Country(Base):
    __tablename__ = "countries"

    nationality_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nationality_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class League(Base):
    __tablename__ = "leagues"

    league_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    league_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class Club(Base):
    __tablename__ = "clubs"

    club_team_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    club_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    league_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("leagues.league_id"), nullable=True
    )

    league: Mapped[League | None] = relationship(lazy="joined")


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_positions: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    potential: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    value_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    wage_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    age: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_face_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    club_team_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("clubs.club_team_id"), nullable=True
    )
    nationality_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("countries.nationality_id"), nullable=True
    )

    club: Mapped[Club | None] = relationship(lazy="joined")
    country: Mapped[Country | None] = relationship(lazy="joined")
