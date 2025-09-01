"""add creator_id to data_list and FK to user

Revision ID: add_creator_to_datalist
Revises: add_unique_constraint_category_data
Create Date: 2025-09-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_creator_to_datalist'
down_revision = 'add_unique_constraint_category_data'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if 'data_list' in insp.get_table_names():
        cols = [c['name'] for c in insp.get_columns('data_list')]
        with op.batch_alter_table('data_list') as batch_op:
            if 'creator_id' not in cols:
                batch_op.add_column(sa.Column('creator_id', sa.Integer(), nullable=True))
            fks = [fk['name'] for fk in insp.get_foreign_keys('data_list') if fk.get('name')]
            if 'fk_data_list_creator_id_user' not in fks:
                batch_op.create_foreign_key(
                    'fk_data_list_creator_id_user', 'user', ['creator_id'], ['id']
                )


def downgrade():
    with op.batch_alter_table('data_list') as batch_op:
        batch_op.drop_constraint('fk_data_list_creator_id_user', type_='foreignkey')
        batch_op.drop_column('creator_id')

