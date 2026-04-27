"""add moderation read receipts and indexes

Revision ID: f26cb2f12c91
Revises: a91f0f6b2d2e
Create Date: 2026-03-31 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f26cb2f12c91"
down_revision: Union[str, Sequence[str], None] = "a91f0f6b2d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("read_at", sa.DateTime(), nullable=True))

    op.create_table(
        "user_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blocker_id", sa.Integer(), nullable=False),
        sa.Column("blocked_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),
    )
    op.create_index(op.f("ix_user_blocks_id"), "user_blocks", ["id"], unique=False)
    op.create_index(op.f("ix_user_blocks_blocker_id"), "user_blocks", ["blocker_id"], unique=False)
    op.create_index(op.f("ix_user_blocks_blocked_id"), "user_blocks", ["blocked_id"], unique=False)

    op.create_table(
        "user_mutes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("muter_id", sa.Integer(), nullable=False),
        sa.Column("muted_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["muted_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("muter_id", "muted_id", name="uq_user_mute"),
    )
    op.create_index(op.f("ix_user_mutes_id"), "user_mutes", ["id"], unique=False)
    op.create_index(op.f("ix_user_mutes_muter_id"), "user_mutes", ["muter_id"], unique=False)
    op.create_index(op.f("ix_user_mutes_muted_id"), "user_mutes", ["muted_id"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("target_post_id", sa.Integer(), nullable=True),
        sa.Column("target_comment_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_comment_id"], ["comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"], unique=False)
    op.create_index(op.f("ix_reports_reporter_id"), "reports", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_reports_target_user_id"), "reports", ["target_user_id"], unique=False)
    op.create_index(op.f("ix_reports_target_post_id"), "reports", ["target_post_id"], unique=False)
    op.create_index(op.f("ix_reports_target_comment_id"), "reports", ["target_comment_id"], unique=False)

    op.create_index("ix_posts_created_at_author_id", "posts", ["created_at", "author_id"], unique=False)
    op.create_index("ix_likes_post_id_user_id", "likes", ["post_id", "user_id"], unique=False)
    op.create_index("ix_bookmarks_user_id_post_id", "bookmarks", ["user_id", "post_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookmarks_user_id_post_id", table_name="bookmarks")
    op.drop_index("ix_likes_post_id_user_id", table_name="likes")
    op.drop_index("ix_posts_created_at_author_id", table_name="posts")

    op.drop_index(op.f("ix_reports_target_comment_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_target_post_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_target_user_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_reporter_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_user_mutes_muted_id"), table_name="user_mutes")
    op.drop_index(op.f("ix_user_mutes_muter_id"), table_name="user_mutes")
    op.drop_index(op.f("ix_user_mutes_id"), table_name="user_mutes")
    op.drop_table("user_mutes")

    op.drop_index(op.f("ix_user_blocks_blocked_id"), table_name="user_blocks")
    op.drop_index(op.f("ix_user_blocks_blocker_id"), table_name="user_blocks")
    op.drop_index(op.f("ix_user_blocks_id"), table_name="user_blocks")
    op.drop_table("user_blocks")

    op.drop_column("messages", "read_at")
