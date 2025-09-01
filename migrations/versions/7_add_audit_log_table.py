"""create audit log table

Revision ID: add_audit_log_table
Revises: add_creator_to_datalist
Create Date: 2025-09-01 00:05:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_audit_log_table'
down_revision = 'add_creator_to_datalist'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('audit_log'):
        op.create_table(
            'audit_log',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id')),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('target_type', sa.String(length=20), nullable=False),
            sa.Column('target_id', sa.Integer()),
            sa.Column('list_id', sa.Integer(), sa.ForeignKey('list_model.id'), nullable=True),
            sa.Column('details', sa.String(length=255)),
        )


def downgrade():
    op.drop_table('audit_log')

