"""add profile fields to users

Revision ID: d4e2b1c9f3a7
Revises: c7f9a83e1b21
Create Date: 2026-03-31 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e2b1c9f3a7"
down_revision: Union[str, Sequence[str], None] = "c7f9a83e1b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bio", sa.String(300), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("cover_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "cover_url")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "bio")
