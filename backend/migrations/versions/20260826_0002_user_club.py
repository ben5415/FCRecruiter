"""Assign one managed club to every account."""
from alembic import op
import sqlalchemy as sa

revision = "20260826_0002"
down_revision = "20260825_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("managed_club_team_id", sa.BigInteger(), nullable=False, server_default="11"),
    )
    op.create_foreign_key(
        "fk_users_managed_club_team_id_clubs",
        "users", "clubs", ["managed_club_team_id"], ["club_team_id"],
    )
    op.alter_column("users", "managed_club_team_id", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_users_managed_club_team_id_clubs", "users", type_="foreignkey")
    op.drop_column("users", "managed_club_team_id")
