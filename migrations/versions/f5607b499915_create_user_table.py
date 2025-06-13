"""create user table

Revision ID: f5607b499915
Revises: 
Create Date: 2025-06-13 07:53:58.263975

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5607b499915'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=80), nullable=False, unique=True),
        sa.Column('email', sa.String(length=120), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=128), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('first_login', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )


def downgrade():
    op.drop_table('user')
