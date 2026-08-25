"""Make usernames globally unique for tenant-free login."""
from alembic import op


revision = "20260826_0006"
down_revision = "20260826_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM users
                GROUP BY username_normalized
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Cannot make usernames global: duplicate usernames exist across tenants';
            END IF;
        END $$
        """
    )
    op.drop_index("uq_users_tenant_username_normalized", table_name="users")
    op.create_index(
        "uq_users_username_normalized",
        "users",
        ["username_normalized"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_username_normalized", table_name="users")
    op.create_index(
        "uq_users_tenant_username_normalized",
        "users",
        ["tenant_id", "username_normalized"],
        unique=True,
    )
