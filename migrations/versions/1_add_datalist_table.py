"""add datalist table

Revision ID: add_datalist_table
Revises: f5607b499915
Create Date: 2025-06-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_datalist_table'
down_revision = 'f5607b499915'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'data_list',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('data', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255)),
        sa.Column('date', sa.Date(), nullable=False),
    )


def downgrade():
    op.drop_table('data_list')
