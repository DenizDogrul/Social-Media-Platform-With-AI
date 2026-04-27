"""add privacy and repost

Revision ID: 8e9c3f5a2b1d
Revises: d4e2b1c9f3a7
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e9c3f5a2b1d'
down_revision = 'd4e2b1c9f3a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add privacy columns to users table
    op.add_column('users', sa.Column('is_private', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('allow_dms_from', sa.String(length=20), nullable=False, server_default='everyone'))
    
    # Create reposts table
    op.create_table(
        'reposts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('original_post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['original_post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_reposts_author_id'), 'reposts', ['author_id'])
    op.create_index(op.f('ix_reposts_post_id'), 'reposts', ['post_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_reposts_post_id'), table_name='reposts')
    op.drop_index(op.f('ix_reposts_author_id'), table_name='reposts')
    op.drop_table('reposts')
    op.drop_column('users', 'allow_dms_from')
    op.drop_column('users', 'is_private')
