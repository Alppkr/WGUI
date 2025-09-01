"""create schedule settings table

Revision ID: add_schedule_settings_table
Revises: add_audit_log_table
Create Date: 2025-09-01 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_schedule_settings_table'
down_revision = 'add_audit_log_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('schedule_settings'):
        op.create_table(
            'schedule_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('hour', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('minute', sa.Integer(), nullable=False, server_default='0'),
        )


def downgrade():
    op.drop_table('schedule_settings')

