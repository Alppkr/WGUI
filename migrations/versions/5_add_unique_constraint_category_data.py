"""add unique constraint for data per category

Revision ID: add_unique_constraint_category_data
Revises: add_email_settings_table
Create Date: 2025-06-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_unique_constraint_category_data'
down_revision = 'add_email_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'data_list' in insp.get_table_names():
        op.create_unique_constraint('uix_category_data', 'data_list', ['category', 'data'])


def downgrade():
    op.drop_constraint('uix_category_data', 'data_list', type_='unique')
