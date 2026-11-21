"""Replace account-owned clubs with team tenants.

Each tenant owns exactly one club and contains multiple users. Existing users
are grouped by their current managed club during the migration.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260826_0003"
down_revision = "20260826_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column(
            "club_team_id",
            sa.BigInteger(),
            sa.ForeignKey("clubs.club_team_id"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("uq_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index(
        "uq_tenants_club_team_id", "tenants", ["club_team_id"], unique=True
    )

    op.add_column("users", sa.Column("tenant_id", sa.BigInteger(), nullable=True))
    op.execute(
        """
        INSERT INTO tenants (name, slug, club_team_id)
        SELECT COALESCE(c.club_name, 'Club ' || u.managed_club_team_id::text),
               'club-' || u.managed_club_team_id::text,
               u.managed_club_team_id
        FROM (SELECT DISTINCT managed_club_team_id FROM users) AS u
        LEFT JOIN clubs AS c ON c.club_team_id = u.managed_club_team_id
        """
    )
    op.execute(
        """
        UPDATE users AS u
        SET tenant_id = t.id
        FROM tenants AS t
        WHERE t.club_team_id = u.managed_club_team_id
        """
    )
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_users_tenant_id_tenants",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.drop_index("uq_users_username_normalized", table_name="users")
    op.create_index(
        "uq_users_tenant_username_normalized",
        "users",
        ["tenant_id", "username_normalized"],
        unique=True,
    )
    op.drop_constraint(
        "fk_users_managed_club_team_id_clubs", "users", type_="foreignkey"
    )
    op.drop_column("users", "managed_club_team_id")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("managed_club_team_id", sa.BigInteger(), nullable=True)
    )
    op.execute(
        """
        UPDATE users AS u
        SET managed_club_team_id = t.club_team_id
        FROM tenants AS t
        WHERE t.id = u.tenant_id
        """
    )
    op.alter_column("users", "managed_club_team_id", nullable=False)
    op.create_foreign_key(
        "fk_users_managed_club_team_id_clubs",
        "users",
        "clubs",
        ["managed_club_team_id"],
        ["club_team_id"],
    )
    op.drop_index("uq_users_tenant_username_normalized", table_name="users")
    op.create_index(
        "uq_users_username_normalized",
        "users",
        ["username_normalized"],
        unique=True,
    )
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")
