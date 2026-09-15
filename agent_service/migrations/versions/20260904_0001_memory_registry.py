"""create short-term memory and agent definition registry

Revision ID: 20260904_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    thread_status = sa.Enum("active", "archived", name="thread_status")
    message_role = sa.Enum("system", "user", "assistant", "tool", name="message_role")
    definition_status = sa.Enum("draft", "active", "disabled", name="agent_definition_status")

    op.create_table(
        "agent_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("tool_names", sa.JSON(), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False),
        sa.Column("status", definition_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_key", "version", name="uq_agent_definition_key_version"),
    )
    op.create_index("ix_agent_definitions_agent_key", "agent_definitions", ["agent_key"])
    op.create_index(
        "uq_agent_definition_one_active",
        "agent_definitions",
        ["agent_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "conversation_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_key", sa.String(80), nullable=False),
        sa.Column("agent_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("status", thread_status, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("current_summary_version", sa.Integer(), nullable=False),
        sa.Column("summarized_through_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_threads_tenant_user",
        "conversation_threads",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(64)),
        sa.Column("tool_call_id", sa.String(128)),
        sa.Column("message_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "sequence", name="uq_message_thread_sequence"),
    )
    op.create_index(
        "ix_conversation_messages_thread_sequence",
        "conversation_messages",
        ["thread_id", "sequence"],
    )

    op.create_table(
        "thread_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summarized_through_sequence", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id", "version", name="uq_thread_summary_version"),
    )


def downgrade() -> None:
    op.drop_table("thread_summaries")
    op.drop_index("ix_conversation_messages_thread_sequence", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversation_threads_tenant_user", table_name="conversation_threads")
    op.drop_table("conversation_threads")
    op.drop_index("uq_agent_definition_one_active", table_name="agent_definitions")
    op.drop_index("ix_agent_definitions_agent_key", table_name="agent_definitions")
    op.drop_table("agent_definitions")
    sa.Enum(name="message_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="thread_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agent_definition_status").drop(op.get_bind(), checkfirst=True)
