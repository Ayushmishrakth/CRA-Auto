"""cra parameter engine foundation

Revision ID: 13a_cra_parameter_engine_foundation
Revises: 12a_tenant_redirect_uri_diagnostics
Create Date: 2026-05-31 05:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "13a_cra_parameter_engine_foundation"
down_revision: Union[str, Sequence[str], None] = "12a_tenant_redirect_uri_diagnostics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("cra_parameter_versions"):
        op.create_table(
            "cra_parameter_versions",
            sa.Column("version", sa.String(length=100), nullable=False),
            sa.Column("source_filename", sa.String(length=500), nullable=False),
            sa.Column("source_hash", sa.String(length=128), nullable=False),
            sa.Column("imported_by", sa.Uuid(), nullable=True),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("validation_report", sa.JSON(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["imported_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version"),
        )
        op.create_index(op.f("ix_cra_parameter_versions_id"), "cra_parameter_versions", ["id"], unique=False)
        op.create_index(op.f("ix_cra_parameter_versions_imported_by"), "cra_parameter_versions", ["imported_by"], unique=False)
        op.create_index(op.f("ix_cra_parameter_versions_is_active"), "cra_parameter_versions", ["is_active"], unique=False)
        op.create_index(op.f("ix_cra_parameter_versions_source_hash"), "cra_parameter_versions", ["source_hash"], unique=False)
        op.create_index(op.f("ix_cra_parameter_versions_version"), "cra_parameter_versions", ["version"], unique=True)

    if not _has_table("cra_parameters"):
        op.create_table(
            "cra_parameters",
            sa.Column("version_id", sa.Uuid(), nullable=False),
            sa.Column("parameter_key", sa.String(length=150), nullable=False),
            sa.Column("display_name", sa.String(length=500), nullable=False),
            sa.Column("domain", sa.String(length=100), nullable=False),
            sa.Column("category", sa.String(length=150), nullable=True),
            sa.Column("technology", sa.String(length=150), nullable=True),
            sa.Column("severity", sa.String(length=50), nullable=False),
            sa.Column("weight", sa.Numeric(10, 4), nullable=False),
            sa.Column("pass_criteria", sa.Text(), nullable=True),
            sa.Column("fail_criteria", sa.Text(), nullable=True),
            sa.Column("criteria_expression", sa.JSON(), nullable=True),
            sa.Column("collector_type", sa.String(length=50), nullable=False),
            sa.Column("graph_endpoint", sa.String(length=1000), nullable=True),
            sa.Column("powershell_mapping", sa.String(length=500), nullable=True),
            sa.Column("portal_mapping", sa.Text(), nullable=True),
            sa.Column("expected_output", sa.Text(), nullable=True),
            sa.Column("copilot_relevance", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("source_ref", sa.JSON(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["version_id"], ["cra_parameter_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("version_id", "parameter_key", name="uq_cra_parameters_version_key"),
        )
        op.create_index("ix_cra_parameters_version_active", "cra_parameters", ["version_id", "is_active"], unique=False)
        op.create_index(op.f("ix_cra_parameters_category"), "cra_parameters", ["category"], unique=False)
        op.create_index(op.f("ix_cra_parameters_collector_type"), "cra_parameters", ["collector_type"], unique=False)
        op.create_index(op.f("ix_cra_parameters_domain"), "cra_parameters", ["domain"], unique=False)
        op.create_index(op.f("ix_cra_parameters_id"), "cra_parameters", ["id"], unique=False)
        op.create_index(op.f("ix_cra_parameters_is_active"), "cra_parameters", ["is_active"], unique=False)
        op.create_index(op.f("ix_cra_parameters_parameter_key"), "cra_parameters", ["parameter_key"], unique=False)
        op.create_index(op.f("ix_cra_parameters_severity"), "cra_parameters", ["severity"], unique=False)
        op.create_index(op.f("ix_cra_parameters_version_id"), "cra_parameters", ["version_id"], unique=False)

    if not _has_table("cra_parameter_evidence"):
        op.create_table(
            "cra_parameter_evidence",
            sa.Column("assessment_id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("parameter_id", sa.Uuid(), nullable=False),
            sa.Column("collector_type", sa.String(length=50), nullable=False),
            sa.Column("graph_endpoint", sa.String(length=1000), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("raw_response", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
            sa.ForeignKeyConstraint(["parameter_id"], ["cra_parameters.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_cra_parameter_evidence_assessment_parameter", "cra_parameter_evidence", ["assessment_id", "parameter_id"], unique=False)
        op.create_index("ix_cra_parameter_evidence_tenant_collected", "cra_parameter_evidence", ["tenant_id", "collected_at"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_assessment_id"), "cra_parameter_evidence", ["assessment_id"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_collected_at"), "cra_parameter_evidence", ["collected_at"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_collector_type"), "cra_parameter_evidence", ["collector_type"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_id"), "cra_parameter_evidence", ["id"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_parameter_id"), "cra_parameter_evidence", ["parameter_id"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_status"), "cra_parameter_evidence", ["status"], unique=False)
        op.create_index(op.f("ix_cra_parameter_evidence_tenant_id"), "cra_parameter_evidence", ["tenant_id"], unique=False)

    if not _has_table("cra_assessment_results"):
        op.create_table(
            "cra_assessment_results",
            sa.Column("assessment_id", sa.Uuid(), nullable=False),
            sa.Column("parameter_id", sa.Uuid(), nullable=False),
            sa.Column("evidence_id", sa.Uuid(), nullable=True),
            sa.Column("score", sa.Numeric(10, 4), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("severity", sa.String(length=50), nullable=False),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("gap_analysis", sa.Text(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("criteria_snapshot", sa.JSON(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
            sa.ForeignKeyConstraint(["evidence_id"], ["cra_parameter_evidence.id"]),
            sa.ForeignKeyConstraint(["parameter_id"], ["cra_parameters.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("assessment_id", "parameter_id", name="uq_cra_assessment_results_assessment_parameter"),
        )
        op.create_index("ix_cra_assessment_results_assessment_status", "cra_assessment_results", ["assessment_id", "status"], unique=False)
        op.create_index("ix_cra_assessment_results_tenant_evaluated", "cra_assessment_results", ["tenant_id", "evaluated_at"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_assessment_id"), "cra_assessment_results", ["assessment_id"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_evaluated_at"), "cra_assessment_results", ["evaluated_at"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_evidence_id"), "cra_assessment_results", ["evidence_id"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_id"), "cra_assessment_results", ["id"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_parameter_id"), "cra_assessment_results", ["parameter_id"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_severity"), "cra_assessment_results", ["severity"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_status"), "cra_assessment_results", ["status"], unique=False)
        op.create_index(op.f("ix_cra_assessment_results_tenant_id"), "cra_assessment_results", ["tenant_id"], unique=False)


def downgrade() -> None:
    for table_name in [
        "cra_assessment_results",
        "cra_parameter_evidence",
        "cra_parameters",
        "cra_parameter_versions",
    ]:
        if _has_table(table_name):
            op.drop_table(table_name)
