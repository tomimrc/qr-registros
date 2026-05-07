"""initial_schema_with_crm_module

Revision ID: 60d047b49f5d
Revises: 
Create Date: 2026-04-23 12:36:46.626607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60d047b49f5d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CRM Professionals table
    op.create_table(
        'crm_professionals',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role_label', sa.String(120), nullable=True),
        sa.Column('specialty', sa.String(120), nullable=True),
        sa.Column('calendar_color', sa.String(20), nullable=False, server_default='#1d4ed8'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_crm_professionals_active', 'active'),
        sa.Index('ix_crm_professionals_name', 'name'),
        sa.Index('ix_crm_professionals_tenant_id', 'tenant_id'),
    )

    # CRM Client Files table
    op.create_table(
        'crm_client_files',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_kind', sa.String(50), nullable=False, server_default='client'),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('reference_code', sa.String(100), nullable=True),
        sa.Column('document_id', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_crm_client_files_display_name', 'display_name'),
        sa.Index('ix_crm_client_files_reference_code', 'reference_code'),
        sa.Index('ix_crm_client_files_status', 'status'),
        sa.Index('ix_crm_client_files_subject_kind', 'subject_kind'),
        sa.Index('ix_crm_client_files_tenant_id', 'tenant_id'),
    )

    # CRM Appointments table
    op.create_table(
        'crm_appointments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('professional_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_admin_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='scheduled'),
        sa.Column('source', sa.String(30), nullable=False, server_default='internal'),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['professional_id'], ['crm_professionals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['crm_client_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_crm_appointments_created_by_admin_id', 'created_by_admin_id'),
        sa.Index('ix_crm_appointments_professional_id', 'professional_id'),
        sa.Index('ix_crm_appointments_starts_at', 'starts_at'),
        sa.Index('ix_crm_appointments_status', 'status'),
        sa.Index('ix_crm_appointments_subject_id', 'subject_id'),
        sa.Index('ix_crm_appointments_tenant_id', 'tenant_id'),
    )

    # CRM Visit Reports table
    op.create_table(
        'crm_visit_reports',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('professional_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('appointment_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_admin_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('actions_taken', sa.Text(), nullable=True),
        sa.Column('next_steps', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(120), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['appointment_id'], ['crm_appointments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['admins.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['professional_id'], ['crm_professionals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['crm_client_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_crm_visit_reports_appointment_id', 'appointment_id'),
        sa.Index('ix_crm_visit_reports_created_by_admin_id', 'created_by_admin_id'),
        sa.Index('ix_crm_visit_reports_occurred_at', 'occurred_at'),
        sa.Index('ix_crm_visit_reports_professional_id', 'professional_id'),
        sa.Index('ix_crm_visit_reports_subject_id', 'subject_id'),
        sa.Index('ix_crm_visit_reports_tenant_id', 'tenant_id'),
    )


def downgrade() -> None:
    op.drop_table('crm_visit_reports')
    op.drop_table('crm_appointments')
    op.drop_table('crm_client_files')
    op.drop_table('crm_professionals')
