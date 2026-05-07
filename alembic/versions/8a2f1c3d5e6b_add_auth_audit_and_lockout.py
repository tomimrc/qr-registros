"""add_auth_audit_and_lockout

Revision ID: 8a2f1c3d5e6b
Revises: 7b88a4d7b7e2
Create Date: 2026-05-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8a2f1c3d5e6b'
down_revision: Union[str, None] = '7b88a4d7b7e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add fields to admins table
    op.add_column('admins', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('admins', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))

    # Create admin_password_history table
    op.create_table(
        'admin_password_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('changed_by', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_admin_password_history_admin_id', 'admin_id'),
        sa.Index('ix_admin_password_history_changed_at', 'changed_at'),
        sa.Index('ix_admin_password_history_tenant_id', 'tenant_id'),
    )

    # Create auth_audit_logs table
    op.create_table(
        'auth_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_auth_audit_logs_admin_id', 'admin_id'),
        sa.Index('ix_auth_audit_logs_event_type', 'event_type'),
        sa.Index('ix_auth_audit_logs_tenant_id', 'tenant_id'),
        sa.Index('ix_auth_audit_logs_timestamp', 'timestamp'),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table('auth_audit_logs')
    op.drop_table('admin_password_history')

    # Drop columns from admins table
    op.drop_column('admins', 'locked_until')
    op.drop_column('admins', 'failed_login_attempts')
