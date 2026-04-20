"""Phase H 도메인 테이블 — notifications, reviews, meeting_attendances, connections,
chat_rooms, chat_participants, chat_messages + users.notification_prefs JSON.

Revision ID: 0003_phase_h
Revises: 0002_user_tags_job
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_phase_h"
down_revision: str | None = "0002_user_tags_job"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("notification_prefs", sa.JSON(), nullable=True),
    )

    notification_type = sa.Enum(
        "participant_pending",
        "participant_approved",
        "participant_rejected",
        "participant_left",
        "review_requested",
        "new_message",
        "connection_requested",
        "connection_accepted",
        name="notification_type",
        native_enum=False,
        length=40,
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=26),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewee_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "meeting_id", "reviewer_id", "reviewee_id", name="uq_reviews_triplet"
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_reviews_meeting_id", "reviews", ["meeting_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])
    op.create_index("ix_reviews_reviewee_id", "reviews", ["reviewee_id"])

    attendance_status = sa.Enum(
        "attended",
        "no_show",
        name="attendance_status",
        native_enum=False,
        length=20,
    )
    op.create_table(
        "meeting_attendances",
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
        sa.Column("status", attendance_status, nullable=False),
        sa.Column(
            "marked_by",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "marked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "meeting_id", "user_id", name="uq_attendance_meeting_user"
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "ix_meeting_attendances_meeting_id", "meeting_attendances", ["meeting_id"]
    )
    op.create_index(
        "ix_meeting_attendances_user_id", "meeting_attendances", ["user_id"]
    )

    connection_status = sa.Enum(
        "pending",
        "accepted",
        name="connection_status",
        native_enum=False,
        length=20,
    )
    op.create_table(
        "connections",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "follower_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "following_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", connection_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "follower_id", "following_id", name="uq_connections_pair"
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_connections_follower_id", "connections", ["follower_id"])
    op.create_index("ix_connections_following_id", "connections", ["following_id"])
    op.create_index("ix_connections_status", "connections", ["status"])

    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(length=26),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("meeting_id", name="uq_chat_rooms_meeting"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_chat_rooms_meeting_id", "chat_rooms", ["meeting_id"])

    op.create_table(
        "chat_participants",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "room_id",
            sa.String(length=26),
            sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "room_id", "user_id", name="uq_chat_participants_pair"
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_chat_participants_room_id", "chat_participants", ["room_id"])
    op.create_index("ix_chat_participants_user_id", "chat_participants", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "room_id",
            sa.String(length=26),
            sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_chat_messages_room_id", "chat_messages", ["room_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_room_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_participants_user_id", table_name="chat_participants")
    op.drop_index("ix_chat_participants_room_id", table_name="chat_participants")
    op.drop_table("chat_participants")

    op.drop_index("ix_chat_rooms_meeting_id", table_name="chat_rooms")
    op.drop_table("chat_rooms")

    op.drop_index("ix_connections_status", table_name="connections")
    op.drop_index("ix_connections_following_id", table_name="connections")
    op.drop_index("ix_connections_follower_id", table_name="connections")
    op.drop_table("connections")

    op.drop_index(
        "ix_meeting_attendances_user_id", table_name="meeting_attendances"
    )
    op.drop_index(
        "ix_meeting_attendances_meeting_id", table_name="meeting_attendances"
    )
    op.drop_table("meeting_attendances")

    op.drop_index("ix_reviews_reviewee_id", table_name="reviews")
    op.drop_index("ix_reviews_reviewer_id", table_name="reviews")
    op.drop_index("ix_reviews_meeting_id", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_column("users", "notification_prefs")
