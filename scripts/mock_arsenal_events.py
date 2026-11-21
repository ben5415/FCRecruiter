"""Insert an idempotent set of Arsenal team events for January-July 2025.

Run from the project root with:

    PYTHONPATH=backend .venv/bin/python scripts/mock_arsenal_events.py --dry-run
    PYTHONPATH=backend .venv/bin/python scripts/mock_arsenal_events.py

The script writes directly to the configured multitenant database. Existing
mock events with the same natural key are skipped, so rerunning it is safe.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import unicodedata

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.modules.auth.models import Tenant, User, UserRole
from app.modules.events.models import TeamEvent, TeamEventType
from app.modules.players.models import Club, Player


@dataclass(frozen=True)
class MockEvent:
    event_type: TeamEventType
    event_date: date
    player_name: str | None = None
    description: str | None = None
    recovery_days: int | None = None
    training_project: str | None = None
    training_effect: int | None = None


MOCK_EVENTS = (
    MockEvent(TeamEventType.MEDICAL, date(2025, 1, 12), "Saka", "Hamstring tightness observed after the match; reduced loading prescribed.", 14),
    MockEvent(TeamEventType.TRAINING, date(2025, 1, 22), "Rice", training_project="Defensive transitions and second-ball recovery", training_effect=8),
    MockEvent(TeamEventType.DRESSING_ROOM, date(2025, 1, 30), description="The squad agreed to improve communication when protecting narrow leads."),
    MockEvent(TeamEventType.MEDICAL, date(2025, 2, 8), "Timber", "Minor ankle sprain during training; individual rehabilitation programme started.", 12),
    MockEvent(TeamEventType.TRAINING, date(2025, 2, 19), "Odegaard", training_project="Chance creation against a compact low block", training_effect=9),
    MockEvent(TeamEventType.DRESSING_ROOM, date(2025, 2, 27), description="Positive response in the team meeting after a difficult run of fixtures."),
    MockEvent(TeamEventType.TRAINING, date(2025, 3, 12), "Saliba", training_project="Progressive build-up under an aggressive press", training_effect=8),
    MockEvent(TeamEventType.MEDICAL, date(2025, 3, 18), "Havertz", "Muscular discomfort; player removed from full training as a precaution.", 21),
    MockEvent(TeamEventType.DRESSING_ROOM, date(2025, 4, 9), description="Senior players led a discussion about maintaining intensity through the final matches."),
    MockEvent(TeamEventType.TRAINING, date(2025, 4, 16), "Saka", training_project="Final-third combinations and weak-foot finishing", training_effect=9),
    MockEvent(TeamEventType.MEDICAL, date(2025, 5, 10), "Saliba", "Low-grade hamstring strain confirmed following assessment.", 17),
    MockEvent(TeamEventType.TRAINING, date(2025, 5, 21), "Timber", training_project="Inverted full-back positioning and counter-pressing", training_effect=8),
    MockEvent(TeamEventType.DRESSING_ROOM, date(2025, 5, 29), description="End-of-season review completed; the group identified consistency as the main improvement area."),
    MockEvent(TeamEventType.TRAINING, date(2025, 6, 11), "Havertz", training_project="Penalty-box movement and first-time finishing", training_effect=7),
    MockEvent(TeamEventType.MEDICAL, date(2025, 7, 3), "Martinelli", "Contact injury to the lower leg; scans showed no structural damage.", 8),
    MockEvent(TeamEventType.TRAINING, date(2025, 7, 16), "Martinelli", training_project="High pressing triggers and recovery runs", training_effect=8),
    MockEvent(TeamEventType.DRESSING_ROOM, date(2025, 7, 21), description="Pre-season meeting welcomed new arrivals and established leadership responsibilities."),
)


def normalized(value: str) -> str:
    translated = value.translate(str.maketrans({"Ø": "O", "ø": "o", "Đ": "D", "đ": "d"}))
    return "".join(
        character for character in unicodedata.normalize("NFKD", translated)
        if not unicodedata.combining(character)
    ).casefold()


def find_arsenal_tenant(session: Session) -> Tenant:
    tenants = session.scalars(select(Tenant).join(Club).where(Club.club_name.ilike("Arsenal"))).all()
    if len(tenants) != 1:
        raise SystemExit(f"Expected one Arsenal tenant, found {len(tenants)}")
    return tenants[0]


def find_player(roster: list[Player], search_name: str) -> Player:
    needle = normalized(search_name)
    matches = [
        player for player in roster
        if needle in normalized(" ".join(filter(None, (player.short_name, player.long_name))))
    ]
    if len(matches) != 1:
        names = ", ".join(player.short_name or str(player.player_id) for player in matches) or "none"
        raise SystemExit(f"Player lookup {search_name!r} returned {len(matches)} matches: {names}")
    return matches[0]


def already_exists(session: Session, tenant_id: int, event: MockEvent, player_id: int | None) -> bool:
    statement = select(TeamEvent.id).where(
        TeamEvent.tenant_id == tenant_id,
        TeamEvent.event_type == event.event_type,
    )
    if event.event_type == TeamEventType.MEDICAL:
        statement = statement.where(TeamEvent.player_id == player_id, TeamEvent.injury_date == event.event_date)
    elif event.event_type == TeamEventType.TRAINING:
        statement = statement.where(
            TeamEvent.player_id == player_id,
            TeamEvent.event_date == event.event_date,
            TeamEvent.training_project == event.training_project,
        )
    else:
        statement = statement.where(
            TeamEvent.event_date == event.event_date,
            TeamEvent.description == event.description,
        )
    return session.scalar(statement.limit(1)) is not None


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock Arsenal team events from 2025-01 to 2025-07")
    parser.add_argument("--dry-run", action="store_true", help="Validate and display actions without inserting rows")
    args = parser.parse_args()

    database_url = get_settings().effective_database_url
    if not database_url:
        raise SystemExit("DATABASE_URL or MULTITENANT_DATABASE_URL is not configured")

    engine = create_engine(database_url, pool_pre_ping=True)
    with Session(engine) as session:
        tenant = find_arsenal_tenant(session)
        manager = session.scalar(
            select(User)
            .where(User.tenant_id == tenant.id, User.role == UserRole.MANAGER, User.is_active.is_(True))
            .order_by(User.id)
        )
        if manager is None:
            raise SystemExit("The Arsenal tenant needs an active manager before events can be seeded")

        roster = session.scalars(
            select(Player).where(Player.club_team_id == tenant.club_team_id).order_by(Player.player_id)
        ).all()
        required_names = {event.player_name for event in MOCK_EVENTS if event.player_name}
        players = {name: find_player(roster, name) for name in required_names}

        inserted = 0
        skipped = 0
        for event in MOCK_EVENTS:
            player = players.get(event.player_name)
            player_id = player.player_id if player else None
            if already_exists(session, tenant.id, event, player_id):
                skipped += 1
                continue

            occurred_at = datetime.combine(event.event_date, time(hour=12), tzinfo=timezone.utc)
            session.add(TeamEvent(
                tenant_id=tenant.id,
                created_by_user_id=manager.id,
                event_type=event.event_type,
                player_id=player_id,
                injury_date=event.event_date if event.event_type == TeamEventType.MEDICAL else None,
                event_date=event.event_date if event.event_type != TeamEventType.MEDICAL else None,
                description=event.description,
                recovery_days=event.recovery_days,
                training_project=event.training_project,
                training_effect=event.training_effect,
                created_at=occurred_at,
                updated_at=occurred_at,
            ))
            inserted += 1

        if args.dry_run:
            session.rollback()
            action = "Would insert"
        else:
            session.commit()
            action = "Inserted"
        print(f"{action} {inserted} Arsenal events; skipped {skipped} existing events.")


if __name__ == "__main__":
    main()
