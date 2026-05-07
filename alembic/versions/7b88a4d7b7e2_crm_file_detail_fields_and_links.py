"""crm_file_detail_fields_and_links

Revision ID: 7b88a4d7b7e2
Revises: 60d047b49f5d
Create Date: 2026-04-23 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b88a4d7b7e2"
down_revision: Union[str, None] = "60d047b49f5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


coverage_type_enum = sa.Enum("particular", "obra_social", "prepaga", name="crm_coverage_type")


def upgrade() -> None:
    coverage_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "crm_client_files",
        sa.Column("coverage_type", coverage_type_enum, nullable=False, server_default="particular"),
    )
    op.add_column("crm_client_files", sa.Column("coverage_name", sa.String(length=255), nullable=True))
    op.add_column("crm_client_files", sa.Column("affiliate_number", sa.String(length=120), nullable=True))
    op.create_index("ix_crm_client_files_coverage_type", "crm_client_files", ["coverage_type"], unique=False)
    op.create_index("ix_crm_client_files_affiliate_number", "crm_client_files", ["affiliate_number"], unique=False)

    op.create_table(
        "crm_client_file_professionals",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_file_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_file_id"], ["crm_client_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_id"], ["crm_professionals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "client_file_id", "professional_id", name="uq_crm_file_prof_tenant_file_prof"),
    )
    op.create_index("ix_crm_file_prof_tenant_id", "crm_client_file_professionals", ["tenant_id"], unique=False)
    op.create_index("ix_crm_file_prof_client_file_id", "crm_client_file_professionals", ["client_file_id"], unique=False)
    op.create_index("ix_crm_file_prof_professional_id", "crm_client_file_professionals", ["professional_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_file_prof_professional_id", table_name="crm_client_file_professionals")
    op.drop_index("ix_crm_file_prof_client_file_id", table_name="crm_client_file_professionals")
    op.drop_index("ix_crm_file_prof_tenant_id", table_name="crm_client_file_professionals")
    op.drop_table("crm_client_file_professionals")

    op.drop_index("ix_crm_client_files_affiliate_number", table_name="crm_client_files")
    op.drop_index("ix_crm_client_files_coverage_type", table_name="crm_client_files")
    op.drop_column("crm_client_files", "affiliate_number")
    op.drop_column("crm_client_files", "coverage_name")
    op.drop_column("crm_client_files", "coverage_type")

    coverage_type_enum.drop(op.get_bind(), checkfirst=True)
