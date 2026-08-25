"""Ensure every migrated tenant has an initial manager."""
from alembic import op


revision = "20260826_0005"
down_revision = "20260826_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users AS candidate
        SET role = 'manager'::user_role
        WHERE candidate.id IN (
            SELECT min(u.id)
            FROM users AS u
            GROUP BY u.tenant_id
            HAVING NOT EXISTS (
                SELECT 1
                FROM users AS manager
                WHERE manager.tenant_id = u.tenant_id
                  AND manager.role = 'manager'::user_role
            )
        )
        """
    )


def downgrade() -> None:
    # The migration cannot distinguish promoted legacy users from managers
    # created after the upgrade, so role demotion would be unsafe.
    pass
