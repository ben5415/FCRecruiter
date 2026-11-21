"""Introduce tenant-scoped football roles."""
from alembic import op


revision = "20260826_0004"
down_revision = "20260826_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('manager', 'player', 'doctor', 'coach')")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE users ALTER COLUMN role TYPE user_role
        USING (
            CASE role
                WHEN 'admin' THEN 'manager'
                ELSE 'player'
            END
        )::user_role
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'player'::user_role")
    # Authentication semantics changed to require a tenant slug.
    op.execute("DELETE FROM user_sessions")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE users ALTER COLUMN role TYPE varchar(20)
        USING (CASE WHEN role = 'manager' THEN 'admin' ELSE 'user' END)
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'")
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.execute("DROP TYPE user_role")
