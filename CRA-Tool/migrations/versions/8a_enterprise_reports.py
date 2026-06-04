"""phase 8a enterprise reports

Revision ID: 8a_enterprise_reports
Revises: 7a_runtime_foundation
Create Date: 2026-05-27 22:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a_enterprise_reports"
down_revision: Union[str, Sequence[str], None] = "7a_runtime_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_reports",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("report_type", sa.String(length=20), nullable=False),
        sa.Column("report_status", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_reports_assessment_id"), "assessment_reports", ["assessment_id"], unique=False)
    op.create_index("ix_assessment_reports_assessment_type", "assessment_reports", ["assessment_id", "report_type"], unique=False)
    op.create_index(op.f("ix_assessment_reports_generated_at"), "assessment_reports", ["generated_at"], unique=False)
    op.create_index(op.f("ix_assessment_reports_generated_by"), "assessment_reports", ["generated_by"], unique=False)
    op.create_index(op.f("ix_assessment_reports_id"), "assessment_reports", ["id"], unique=False)
    op.create_index("ix_assessment_reports_status", "assessment_reports", ["report_status"], unique=False)
    op.create_index(op.f("ix_assessment_reports_report_type"), "assessment_reports", ["report_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_reports_report_type"), table_name="assessment_reports")
    op.drop_index("ix_assessment_reports_status", table_name="assessment_reports")
    op.drop_index(op.f("ix_assessment_reports_id"), table_name="assessment_reports")
    op.drop_index(op.f("ix_assessment_reports_generated_by"), table_name="assessment_reports")
    op.drop_index(op.f("ix_assessment_reports_generated_at"), table_name="assessment_reports")
    op.drop_index("ix_assessment_reports_assessment_type", table_name="assessment_reports")
    op.drop_index(op.f("ix_assessment_reports_assessment_id"), table_name="assessment_reports")
    op.drop_table("assessment_reports")
