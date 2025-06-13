"""add list model table

Revision ID: add_list_model_table
Revises: add_datalist_table
Create Date: 2025-06-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_list_model_table'
down_revision = 'add_datalist_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('list_model'):
        op.create_table(
            'list_model',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        )


def downgrade():
    op.drop_table('list_model')
