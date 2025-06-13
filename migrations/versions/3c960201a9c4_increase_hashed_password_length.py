"""increase hashed_password length

Revision ID: 3c960201a9c4
Revises: add_type_column
Create Date: 2025-06-13 19:52:56.183885

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c960201a9c4'
down_revision = 'add_type_column'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c['name'] for c in insp.get_columns('user')]
    if 'hashed_password' in cols:
        with op.batch_alter_table('user') as batch_op:
            batch_op.alter_column(
                'hashed_password',
                type_=sa.String(length=200),
                existing_type=sa.String(length=128),
            )


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column(
            'hashed_password',
            type_=sa.String(length=128),
            existing_type=sa.String(length=200),
        )
