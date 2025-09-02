"""create audit settings table

Revision ID: add_audit_settings_table
Revises: add_schedule_settings_table
Create Date: 2025-09-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_audit_settings_table'
down_revision = 'add_schedule_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('audit_settings'):
        op.create_table(
            'audit_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('retention_days', sa.Integer(), nullable=False, server_default='90'),
        )


def downgrade():
    op.drop_table('audit_settings')

