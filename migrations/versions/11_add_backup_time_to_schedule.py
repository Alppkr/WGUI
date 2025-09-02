"""add backup time columns to schedule_settings

Revision ID: add_backup_time_to_schedule
Revises: add_backup_settings_table
Create Date: 2025-09-02 00:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_backup_time_to_schedule'
down_revision = 'add_backup_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('schedule_settings'):
        cols = [c['name'] for c in insp.get_columns('schedule_settings')]
        if 'backup_hour' not in cols:
            op.add_column('schedule_settings', sa.Column('backup_hour', sa.Integer(), nullable=False, server_default='0'))
        if 'backup_minute' not in cols:
            op.add_column('schedule_settings', sa.Column('backup_minute', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('schedule_settings') as batch_op:
        try:
            batch_op.drop_column('backup_hour')
        except Exception:
            pass
        try:
            batch_op.drop_column('backup_minute')
        except Exception:
            pass

