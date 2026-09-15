"""resize knowledge embeddings for Ollama bge-m3

Revision ID: 20260912_0003
Revises: 20260910_0002
"""

from alembic import op


revision = "20260912_0003"
down_revision = "20260910_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 已存在的向量不能转换成另一种模型的向量，迁移前应确保知识库为空。
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute(
        "ALTER TABLE knowledge_chunks "
        "ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute(
        "ALTER TABLE knowledge_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
