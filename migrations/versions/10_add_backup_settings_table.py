"""create backup settings table

Revision ID: add_backup_settings_table
Revises: add_audit_settings_table
Create Date: 2025-09-02 00:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_backup_settings_table'
down_revision = 'add_audit_settings_table'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('backup_settings'):
        op.create_table(
            'backup_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('directory', sa.String(length=255), nullable=False),
            sa.Column('keep', sa.Integer(), nullable=False, server_default='3'),
        )


def downgrade():
    op.drop_table('backup_settings')

