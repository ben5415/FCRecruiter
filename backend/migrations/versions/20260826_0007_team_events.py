"""Add tenant-scoped medical, training and dressing-room events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


revision = "20260826_0007"
down_revision = "20260826_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    event_type = ENUM(
        "medical", "training", "dressing_room",
        name="team_event_type", create_type=False,
    )
    event_type.create(op.get_bind())
    op.create_table(
        "team_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("player_id", sa.BigInteger(), sa.ForeignKey("players.player_id")),
        sa.Column("injury_date", sa.Date()),
        sa.Column("description", sa.Text()),
        sa.Column("recovery_days", sa.Integer()),
        sa.Column("training_project", sa.String(200)),
        sa.Column("training_effect", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("recovery_days IS NULL OR recovery_days >= 0", name="ck_team_events_recovery_days"),
    )
    op.create_index("ix_team_events_tenant_id", "team_events", ["tenant_id"])
    op.create_index("ix_team_events_created_by_user_id", "team_events", ["created_by_user_id"])
    op.create_index("ix_team_events_event_type", "team_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("team_events")
    sa.Enum(name="team_event_type").drop(op.get_bind())
