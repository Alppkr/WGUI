"""add actor_name to audit_log

Revision ID: add_actor_name_to_auditlog
Revises: add_audit_time_to_schedule
Create Date: 2025-09-02 01:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'add_actor_name_to_auditlog'
down_revision = 'add_audit_time_to_schedule'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c['name'] for c in insp.get_columns('audit_log')]
    if 'actor_name' not in cols:
        op.add_column('audit_log', sa.Column('actor_name', sa.String(length=120), nullable=True))


def downgrade():
    with op.batch_alter_table('audit_log') as batch_op:
        try:
            batch_op.drop_column('actor_name')
        except Exception:
            pass

