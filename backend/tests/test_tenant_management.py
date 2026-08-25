from argparse import Namespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.modules.auth.models import Tenant, UserRole
from app.modules.players.models import Club
from app.shared.database import Base
from scripts import manage_tenants


def test_tenant_create_update_delete(monkeypatch) -> None:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(manage_tenants, "getpass", lambda _: "secure-password")

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Club(club_team_id=11, club_name="Manchester United"),
            Club(club_team_id=243, club_name="Real Madrid"),
        ])
        session.commit()
        manage_tenants.create_tenant(session, Namespace(
            name="United Workspace", slug="united", club_id=11,
            manager_username="manager", manager_email=None,
            manager_display_name="Club Manager",
        ))
        tenant = session.scalar(select(Tenant).where(Tenant.slug == "united"))
        assert tenant is not None
        assert tenant.users[0].role is UserRole.MANAGER

        manage_tenants.update_tenant(session, Namespace(
            slug="united", name="Madrid Workspace", new_slug="madrid",
            club_id=243, active=None,
        ))
        assert tenant.slug == "madrid"
        assert tenant.club_team_id == 243

        manage_tenants.delete_tenant(session, Namespace(slug="madrid", yes=True))
        assert session.scalar(select(Tenant)) is None
