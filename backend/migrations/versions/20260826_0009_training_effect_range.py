"""Constrain training effect scores to the inclusive range 0-10."""

from alembic import op


revision = "20260826_0009"
down_revision = "20260826_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_team_events_training_effect_range",
        "team_events",
        "training_effect IS NULL OR training_effect BETWEEN 0 AND 10",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_team_events_training_effect_range",
        "team_events",
        type_="check",
    )
