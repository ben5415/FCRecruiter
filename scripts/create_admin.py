"""Create the initial administrator account interactively."""
from getpass import getpass

from sqlalchemy import or_, select

from app.modules.auth.models import User
from app.modules.auth.security import hash_password, normalize_identifier
from app.shared.database import get_session_factory


def main() -> None:
    username = input("Admin username: ").strip()
    email = input("Email (optional): ").strip() or None
    display_name = input("Display name (optional): ").strip() or None
    club_team_id = int(input("Managed club ID [11]: ").strip() or "11")
    password = getpass("Password (at least 8 characters): ")
    if len(username) < 3 or len(password) < 8:
        raise SystemExit("Username must have 3 characters and password must have 8 characters.")

    normalized_username = normalize_identifier(username)
    normalized_email = normalize_identifier(email) if email else None
    with get_session_factory()() as session:
        from app.modules.players.models import Club
        if session.get(Club, club_team_id) is None:
            raise SystemExit("That club ID does not exist.")
        existing = session.scalar(
            select(User).where(
                or_(
                    User.username_normalized == normalized_username,
                    User.email_normalized == normalized_email if normalized_email else False,
                )
            )
        )
        if existing:
            raise SystemExit("That username or email already exists.")
        session.add(
            User(
                username=username,
                username_normalized=normalized_username,
                email=email,
                email_normalized=normalized_email,
                display_name=display_name,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
                managed_club_team_id=club_team_id,
            )
        )
        session.commit()
    print("Administrator created.")


if __name__ == "__main__":
    main()
