"""initial schema — regions, users, auth, meeting series/meetings/participants.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    ap = sa.Enum(
        "local", "google", name="auth_provider", native_enum=False, length=32
    )
    mm = sa.Enum(
        "offline",
        "online",
        name="meeting_mode",
        native_enum=False,
        length=32,
    )
    mg = sa.Enum(
        "공부",
        "작업",
        "독서",
        "기타",
        name="meeting_goal",
        native_enum=False,
        length=32,
    )
    ms = sa.Enum(
        "recruiting",
        "finished",
        "cancelled",
        name="meeting_status",
        native_enum=False,
        length=32,
    )
    mps = sa.Enum(
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="meeting_participant_status",
        native_enum=False,
        length=32,
    )
    mrf = sa.Enum(
        "WEEKLY",
        "BIWEEKLY",
        "MONTHLY",
        name="meeting_recurrence_frequency",
        native_enum=False,
        length=32,
    )

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sido", sa.String(length=40), nullable=False),
        sa.Column("sigungu", sa.String(length=80), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("full_name", name="uq_regions_full_name"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_regions_sido_sigungu", "regions", ["sido", "sigungu"]
    )
    op.create_index("ix_regions_name", "regions", ["name"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "last_login_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", ap, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_auth_identity_provider_user",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_auth_identities_user_id", "auth_identities", ["user_id"]
    )

    op.create_table(
        "meeting_series",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "host_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mode", mm, nullable=False),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("regions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("location_address", sa.String(length=500), nullable=True),
        sa.Column("goal", mg, nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False),
        sa.Column("frequency", mrf, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("meeting_time", sa.Time(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_participants BETWEEN 2 AND 8",
            name="ck_meeting_series_max_participants_range",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_meeting_series_host_id", "meeting_series", ["host_id"]
    )
    op.create_index("ix_meeting_series_title", "meeting_series", ["title"])
    op.create_index(
        "ix_meeting_series_region_id", "meeting_series", ["region_id"]
    )
    op.create_index("ix_meeting_series_goal", "meeting_series", ["goal"])
    op.create_index(
        "ix_meeting_series_start_date", "meeting_series", ["start_date"]
    )
    op.create_index(
        "ix_meeting_series_deleted_at", "meeting_series", ["deleted_at"]
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "host_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "series_id",
            sa.String(length=26),
            sa.ForeignKey("meeting_series.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("mode", mm, nullable=False),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("regions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column("location_address", sa.String(length=500), nullable=True),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("meeting_time", sa.Time(), nullable=False),
        sa.Column("goal", mg, nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_recurring",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "status",
            ms,
            nullable=False,
            server_default="recruiting",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "active_guard",
            sa.String(length=26),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_participants BETWEEN 2 AND 8",
            name="ck_meetings_max_participants_range",
        ),
        sa.UniqueConstraint(
            "host_id",
            "meeting_date",
            "meeting_time",
            "active_guard",
            name="uq_meetings_host_slot_active",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_meetings_host_id", "meetings", ["host_id"])
    op.create_index("ix_meetings_series_id", "meetings", ["series_id"])
    op.create_index("ix_meetings_title", "meetings", ["title"])
    op.create_index("ix_meetings_region_id", "meetings", ["region_id"])
    op.create_index("ix_meetings_meeting_date", "meetings", ["meeting_date"])
    op.create_index("ix_meetings_goal", "meetings", ["goal"])
    op.create_index("ix_meetings_status", "meetings", ["status"])
    op.create_index("ix_meetings_deleted_at", "meetings", ["deleted_at"])
    op.create_index(
        "ix_meetings_date_time", "meetings", ["meeting_date", "meeting_time"]
    )
    op.create_index(
        "ix_meetings_status_region_date",
        "meetings",
        ["status", "region_id", "meeting_date"],
    )

    op.create_table(
        "meeting_participants",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=26),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            mps,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "meeting_id",
            "user_id",
            name="uq_meeting_participants_meeting_user",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_meeting_participants_meeting_id",
        "meeting_participants",
        ["meeting_id"],
    )
    op.create_index(
        "ix_meeting_participants_user_id",
        "meeting_participants",
        ["user_id"],
    )
    op.create_index(
        "ix_meeting_participants_status",
        "meeting_participants",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meeting_participants_status", table_name="meeting_participants"
    )
    op.drop_index(
        "ix_meeting_participants_user_id", table_name="meeting_participants"
    )
    op.drop_index(
        "ix_meeting_participants_meeting_id",
        table_name="meeting_participants",
    )
    op.drop_table("meeting_participants")

    op.drop_index("ix_meetings_status_region_date", table_name="meetings")
    op.drop_index("ix_meetings_date_time", table_name="meetings")
    op.drop_index("ix_meetings_deleted_at", table_name="meetings")
    op.drop_index("ix_meetings_status", table_name="meetings")
    op.drop_index("ix_meetings_goal", table_name="meetings")
    op.drop_index("ix_meetings_meeting_date", table_name="meetings")
    op.drop_index("ix_meetings_region_id", table_name="meetings")
    op.drop_index("ix_meetings_title", table_name="meetings")
    op.drop_index("ix_meetings_series_id", table_name="meetings")
    op.drop_index("ix_meetings_host_id", table_name="meetings")
    op.drop_table("meetings")

    op.drop_index(
        "ix_meeting_series_deleted_at", table_name="meeting_series"
    )
    op.drop_index("ix_meeting_series_start_date", table_name="meeting_series")
    op.drop_index("ix_meeting_series_goal", table_name="meeting_series")
    op.drop_index("ix_meeting_series_region_id", table_name="meeting_series")
    op.drop_index("ix_meeting_series_title", table_name="meeting_series")
    op.drop_index("ix_meeting_series_host_id", table_name="meeting_series")
    op.drop_table("meeting_series")

    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_table("auth_identities")

    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_regions_name", table_name="regions")
    op.drop_index("ix_regions_sido_sigungu", table_name="regions")
    op.drop_table("regions")
