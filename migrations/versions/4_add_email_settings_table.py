"""create email settings table

Revision ID: add_email_settings_table
Revises: 3c960201a9c4
Create Date: 2025-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_email_settings_table'
down_revision = '3c960201a9c4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('email_settings'):
        op.create_table(
            'email_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('from_email', sa.String(length=120), nullable=False),
            sa.Column('to_email', sa.String(length=120), nullable=False),
            sa.Column('smtp_server', sa.String(length=120), nullable=False),
            sa.Column('smtp_port', sa.Integer(), nullable=False),
            sa.Column('smtp_user', sa.String(length=120)),
            sa.Column('smtp_pass', sa.String(length=120)),
        )


def downgrade():
    op.drop_table('email_settings')
