"""add type column to list model

Revision ID: add_type_column
Revises: add_list_model_table
Create Date: 2025-06-13 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_type_column'
down_revision = 'add_list_model_table'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('list_model', sa.Column('type', sa.String(length=20), nullable=False, server_default='Ip'))
    op.alter_column('list_model', 'type', server_default=None)


def downgrade():
    op.drop_column('list_model', 'type')
