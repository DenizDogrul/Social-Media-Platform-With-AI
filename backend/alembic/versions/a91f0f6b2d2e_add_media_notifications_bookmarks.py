"""add media notifications bookmarks

Revision ID: a91f0f6b2d2e
Revises: 3d7b4f42aceb
Create Date: 2026-03-31 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a91f0f6b2d2e"
down_revision: Union[str, Sequence[str], None] = "3d7b4f42aceb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)

    op.create_table(
        "post_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("media_url", sa.String(length=500), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_media_id"), "post_media", ["id"], unique=False)
    op.create_index(op.f("ix_post_media_post_id"), "post_media", ["post_id"], unique=False)

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "post_id", name="unique_bookmark"),
    )
    op.create_index(op.f("ix_bookmarks_id"), "bookmarks", ["id"], unique=False)
    op.create_index(op.f("ix_bookmarks_post_id"), "bookmarks", ["post_id"], unique=False)
    op.create_index(op.f("ix_bookmarks_user_id"), "bookmarks", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bookmarks_user_id"), table_name="bookmarks")
    op.drop_index(op.f("ix_bookmarks_post_id"), table_name="bookmarks")
    op.drop_index(op.f("ix_bookmarks_id"), table_name="bookmarks")
    op.drop_table("bookmarks")

    op.drop_index(op.f("ix_post_media_post_id"), table_name="post_media")
    op.drop_index(op.f("ix_post_media_id"), table_name="post_media")
    op.drop_table("post_media")

    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
