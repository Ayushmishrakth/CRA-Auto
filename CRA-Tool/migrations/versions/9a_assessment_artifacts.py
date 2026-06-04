"""assessment artifacts

Revision ID: 9a_assessment_artifacts
Revises: 8a_enterprise_reports
Create Date: 2026-05-28 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a_assessment_artifacts"
down_revision: Union[str, Sequence[str], None] = "8a_enterprise_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_artifacts",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("parameter_key", sa.String(length=255), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=True),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("source_script", sa.String(length=500), nullable=True),
        sa.Column("source_csv", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("stdout", sa.String(), nullable=True),
        sa.Column("stderr", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["assessment_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_artifacts_assessment_parameter", "assessment_artifacts", ["assessment_id", "parameter_key"], unique=False)
    op.create_index("ix_assessment_artifacts_tenant_created", "assessment_artifacts", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_artifact_type"), "assessment_artifacts", ["artifact_type"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_assessment_id"), "assessment_artifacts", ["assessment_id"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_id"), "assessment_artifacts", ["id"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_job_id"), "assessment_artifacts", ["job_id"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_parameter_key"), "assessment_artifacts", ["parameter_key"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_status"), "assessment_artifacts", ["status"], unique=False)
    op.create_index(op.f("ix_assessment_artifacts_tenant_id"), "assessment_artifacts", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_artifacts_tenant_id"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_status"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_parameter_key"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_job_id"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_id"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_assessment_id"), table_name="assessment_artifacts")
    op.drop_index(op.f("ix_assessment_artifacts_artifact_type"), table_name="assessment_artifacts")
    op.drop_index("ix_assessment_artifacts_tenant_created", table_name="assessment_artifacts")
    op.drop_index("ix_assessment_artifacts_assessment_parameter", table_name="assessment_artifacts")
    op.drop_table("assessment_artifacts")
