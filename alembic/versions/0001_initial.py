"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2024-03-01 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("username", sa.String(length=64)),
        sa.Column("first_name", sa.String(length=128)),
        sa.Column("last_name", sa.String(length=128)),
        sa.Column("phone", sa.String(length=32)),
        sa.Column("email", sa.String(length=255)),
        sa.Column("timezone", sa.String(length=64)),
        sa.Column("start_payload", sa.String(length=255)),
        sa.Column("utm_source", sa.String(length=128)),
        sa.Column("utm_medium", sa.String(length=128)),
        sa.Column("utm_campaign", sa.String(length=128)),
        sa.Column("utm_content", sa.String(length=128)),
        sa.Column("utm_term", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("teaser", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("image_id", sa.String(length=255), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False, server_default=sa.text("200")),
        sa.Column("subscribed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("attended_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("report_media_id", sa.String(length=255)),
        sa.Column("manager_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("reminder_3d_sent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reminder_1d_sent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("reminder_day_sent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("attended", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_logs_admin_id", "logs", ["admin_id"])

    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer()),
        sa.Column("event_id", sa.Integer()),
        sa.Column("payload", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_index("ix_logs_admin_id", table_name="logs")
    op.drop_table("metrics")
    op.drop_table("logs")
    op.drop_table("subscriptions")
    op.drop_table("events")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
