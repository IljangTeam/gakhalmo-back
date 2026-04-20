"""add users.tags (JSON) and users.job (VARCHAR(100))

Revision ID: 0002_user_tags_job
Revises: 0001_initial
Create Date: 2026-04-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_tags_job"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("job", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("tags", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "tags")
    op.drop_column("users", "job")
