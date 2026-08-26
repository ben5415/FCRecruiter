"""Add one current tactic per tenant."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


revision = "20260826_0010"
down_revision = "20260826_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    formation = ENUM(
        "4-3-3", "4-2-3-1", "4-4-2", "3-4-3", "3-5-2", "5-3-2",
        name="formation", create_type=False,
    )
    playing_style = ENUM(
        "possession", "counter_attack", "high_press", "low_block",
        "wing_play", "direct", "balanced",
        name="playing_style", create_type=False,
    )
    formation.create(op.get_bind())
    playing_style.create(op.get_bind())
    op.create_table(
        "team_tactics",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("formation", formation, nullable=False),
        sa.Column("playing_style", playing_style, nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("updated_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_team_tactics_tenant_id"),
    )


def downgrade() -> None:
    op.drop_table("team_tactics")
    sa.Enum(name="playing_style").drop(op.get_bind())
    sa.Enum(name="formation").drop(op.get_bind())
