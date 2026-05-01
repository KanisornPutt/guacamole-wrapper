"""remove fixed_ip, add workspace OS credentials

Revision ID: 20260501_0002_os_creds
Revises: eeccc3f9ab2f
Create Date: 2026-05-01 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260501_0002_os_creds"
down_revision = "eeccc3f9ab2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("os_username", sa.String(length=255), nullable=True))
    op.add_column("workspaces", sa.Column("os_password", sa.String(length=255), nullable=True))
    op.drop_column("workspaces", "fixed_ip")


def downgrade() -> None:
    op.add_column("workspaces", sa.Column("fixed_ip", sa.String(length=45), nullable=True))
    op.drop_column("workspaces", "os_password")
    op.drop_column("workspaces", "os_username")