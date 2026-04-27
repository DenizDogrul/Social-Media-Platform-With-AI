"""add thumbnail url to post media

Revision ID: c7f9a83e1b21
Revises: f26cb2f12c91
Create Date: 2026-03-31 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7f9a83e1b21"
down_revision: Union[str, Sequence[str], None] = "f26cb2f12c91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("post_media", sa.Column("thumbnail_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("post_media", "thumbnail_url")
