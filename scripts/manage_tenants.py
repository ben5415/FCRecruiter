"""Administrative CLI for tenant CRUD.

This is intentionally not exposed through the web API. The script targets
MULTITENANT_DATABASE_URL when configured, otherwise it derives the new database
name by appending ``_multitenant`` to DATABASE_URL.
"""
import argparse
from getpass import getpass
import os
import re

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.modules.auth.models import Tenant, User, UserRole
from app.modules.auth.security import hash_password, normalize_identifier
from app.modules.players.models import Club


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def database_url():
    load_dotenv()
    explicit = os.getenv("MULTITENANT_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    source = os.getenv("DATABASE_URL")
    if not source:
        raise SystemExit("DATABASE_URL is not configured")
    url = make_url(source)
    if not url.database:
        raise SystemExit("DATABASE_URL must contain a database name")
    target = url.database if url.database.endswith("_multitenant") else f"{url.database}_multitenant"
    return url.set(database=target)


def tenant_by_slug(session: Session, slug: str) -> Tenant:
    tenant = session.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise SystemExit(f"Tenant {slug!r} does not exist")
    return tenant


def list_tenants(session: Session, _: argparse.Namespace) -> None:
    rows = session.execute(
        select(
            Tenant.slug,
            Tenant.name,
            Tenant.club_team_id,
            Tenant.is_active,
            Club.club_name,
            func.count(User.id),
        )
        .join(Tenant.club)
        .outerjoin(Tenant.users)
        .group_by(
            Tenant.slug,
            Tenant.name,
            Tenant.club_team_id,
            Tenant.is_active,
            Club.club_name,
        )
        .order_by(Tenant.name)
    ).all()
    if not rows:
        print("No tenants.")
        return
    for slug, name, club_id, is_active, club_name, user_count in rows:
        state = "active" if is_active else "disabled"
        print(f"{slug}: {name} | {club_name} ({club_id}) | {user_count} users | {state}")


def create_tenant(session: Session, args: argparse.Namespace) -> None:
    if not SLUG_PATTERN.fullmatch(args.slug):
        raise SystemExit("Slug must contain lowercase letters, numbers and single hyphens")
    if session.scalar(select(Tenant).where(Tenant.slug == args.slug)):
        raise SystemExit("That tenant slug already exists")
    club = session.get(Club, args.club_id)
    if club is None:
        raise SystemExit("That club ID does not exist")
    if session.scalar(select(Tenant).where(Tenant.club_team_id == args.club_id)):
        raise SystemExit("That club already belongs to a tenant")
    username_normalized = normalize_identifier(args.manager_username)
    email_normalized = normalize_identifier(args.manager_email) if args.manager_email else None
    if session.scalar(select(User).where(User.username_normalized == username_normalized)):
        raise SystemExit("That username already exists")
    if email_normalized and session.scalar(select(User).where(User.email_normalized == email_normalized)):
        raise SystemExit("That email already exists")
    password = getpass("Initial manager password (at least 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must have at least 8 characters")

    tenant = Tenant(name=args.name.strip(), slug=args.slug, club_team_id=args.club_id, is_active=True)
    tenant.users.append(
        User(
            username=args.manager_username.strip(),
            username_normalized=username_normalized,
            email=args.manager_email,
            email_normalized=email_normalized,
            display_name=args.manager_display_name,
            password_hash=hash_password(password),
            role=UserRole.MANAGER,
            is_active=True,
        )
    )
    session.add(tenant)
    session.commit()
    print(f"Created tenant {tenant.slug!r} with its initial manager.")


def update_tenant(session: Session, args: argparse.Namespace) -> None:
    tenant = tenant_by_slug(session, args.slug)
    if args.name is None and args.new_slug is None and args.club_id is None and args.active is None:
        raise SystemExit("No changes supplied")
    if args.new_slug is not None:
        if not SLUG_PATTERN.fullmatch(args.new_slug):
            raise SystemExit("Slug must contain lowercase letters, numbers and single hyphens")
        duplicate = session.scalar(select(Tenant).where(Tenant.slug == args.new_slug, Tenant.id != tenant.id))
        if duplicate:
            raise SystemExit("That tenant slug already exists")
        tenant.slug = args.new_slug
    if args.name is not None:
        tenant.name = args.name.strip()
    if args.club_id is not None:
        if session.get(Club, args.club_id) is None:
            raise SystemExit("That club ID does not exist")
        duplicate = session.scalar(select(Tenant).where(Tenant.club_team_id == args.club_id, Tenant.id != tenant.id))
        if duplicate:
            raise SystemExit("That club already belongs to a tenant")
        tenant.club_team_id = args.club_id
    if args.active is not None:
        tenant.is_active = args.active
    session.commit()
    print(f"Updated tenant {tenant.slug!r}.")


def delete_tenant(session: Session, args: argparse.Namespace) -> None:
    tenant = tenant_by_slug(session, args.slug)
    if not args.yes:
        confirmation = input(f"Delete tenant {tenant.slug!r} and all its users? Type its slug: ")
        if confirmation != tenant.slug:
            raise SystemExit("Deletion cancelled")
    session.delete(tenant)
    session.commit()
    print(f"Deleted tenant {args.slug!r}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage football club tenants")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.set_defaults(handler=list_tenants)

    create = subparsers.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--slug", required=True)
    create.add_argument("--club-id", required=True, type=int)
    create.add_argument("--manager-username", required=True)
    create.add_argument("--manager-email")
    create.add_argument("--manager-display-name")
    create.set_defaults(handler=create_tenant)

    update = subparsers.add_parser("update")
    update.add_argument("slug")
    update.add_argument("--name")
    update.add_argument("--new-slug")
    update.add_argument("--club-id", type=int)
    active = update.add_mutually_exclusive_group()
    active.add_argument("--activate", dest="active", action="store_true")
    active.add_argument("--disable", dest="active", action="store_false")
    update.set_defaults(active=None, handler=update_tenant)

    delete = subparsers.add_parser("delete")
    delete.add_argument("slug")
    delete.add_argument("--yes", action="store_true")
    delete.set_defaults(handler=delete_tenant)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    engine = create_engine(database_url(), pool_pre_ping=True)
    with Session(engine) as session:
        args.handler(session, args)


if __name__ == "__main__":
    main()
