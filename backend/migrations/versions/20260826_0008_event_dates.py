"""Add dates to training and dressing-room events."""
from alembic import op
import sqlalchemy as sa


revision = "20260826_0008"
down_revision = "20260826_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("team_events", sa.Column("event_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE team_events
        SET event_date = created_at::date
        WHERE event_type IN ('training', 'dressing_room')
          AND event_date IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("team_events", "event_date")
