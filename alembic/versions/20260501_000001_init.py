"""init

Revision ID: 20260501_000001
Revises: 
Create Date: 2026-05-01 00:00:01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260501_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("external_user_id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "workspaces",
        sa.Column("external_instance_id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.external_user_id", ondelete="CASCADE"), nullable=True),
        sa.Column("guacamole_connection_id", sa.Integer(), unique=True),
        sa.Column("workspace_name", sa.String(length=255)),
        sa.Column("fixed_ip", sa.String(length=45)),
        sa.Column("floating_ip", sa.String(length=45), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("workspaces")
    op.drop_table("users")
