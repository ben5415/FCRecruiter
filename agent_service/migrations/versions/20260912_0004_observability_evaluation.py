"""add Agent traces and offline evaluation results

Revision ID: 20260912_0004
Revises: 20260912_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20260912_0004"
down_revision = "20260912_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("agent_version", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_tenant_created", "agent_runs", ["tenant_id", "created_at"])
    op.create_table(
        "agent_trace_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_trace_events_run_id", "agent_trace_events", ["run_id"])
    op.create_table(
        "agent_evaluation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("evaluator", sa.String(40), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_evaluation_results_run_id", "agent_evaluation_results", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_agent_evaluation_results_run_id", table_name="agent_evaluation_results")
    op.drop_table("agent_evaluation_results")
    op.drop_index("ix_agent_trace_events_run_id", table_name="agent_trace_events")
    op.drop_table("agent_trace_events")
    op.drop_index("ix_agent_runs_tenant_created", table_name="agent_runs")
    op.drop_table("agent_runs")
