"""phase 7a runtime foundation

Revision ID: 7a_runtime_foundation
Revises: 1d29ffd7b801
Create Date: 2026-05-27 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a_runtime_foundation"
down_revision: Union[str, Sequence[str], None] = "1d29ffd7b801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_jobs",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_stage", sa.String(length=100), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=False),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_jobs_assessment_id"), "assessment_jobs", ["assessment_id"], unique=False)
    op.create_index("ix_assessment_jobs_assessment_created", "assessment_jobs", ["assessment_id", "created_at"], unique=False)
    op.create_index(op.f("ix_assessment_jobs_created_at"), "assessment_jobs", ["created_at"], unique=False)
    op.create_index(op.f("ix_assessment_jobs_id"), "assessment_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_assessment_jobs_status"), "assessment_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_assessment_jobs_tenant_id"), "assessment_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_assessment_jobs_tenant_status", "assessment_jobs", ["tenant_id", "status"], unique=False)

    op.create_table(
        "assessment_events",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_events_assessment_id"), "assessment_events", ["assessment_id"], unique=False)
    op.create_index("ix_assessment_events_assessment_created", "assessment_events", ["assessment_id", "created_at"], unique=False)
    op.create_index(op.f("ix_assessment_events_created_at"), "assessment_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_assessment_events_event_type"), "assessment_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_assessment_events_id"), "assessment_events", ["id"], unique=False)
    op.create_index(op.f("ix_assessment_events_tenant_id"), "assessment_events", ["tenant_id"], unique=False)
    op.create_index("ix_assessment_events_tenant_created", "assessment_events", ["tenant_id", "created_at"], unique=False)

    op.create_table(
        "assessment_recommendations",
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("parameter_key", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("recommendation_text", sa.String(), nullable=False),
        sa.Column("remediation_steps", sa.JSON(), nullable=True),
        sa.Column("effort", sa.String(length=50), nullable=True),
        sa.Column("impact", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_recommendations_assessment_id"), "assessment_recommendations", ["assessment_id"], unique=False)
    op.create_index("ix_assessment_recommendations_assessment_created", "assessment_recommendations", ["assessment_id", "created_at"], unique=False)
    op.create_index(op.f("ix_assessment_recommendations_created_at"), "assessment_recommendations", ["created_at"], unique=False)
    op.create_index(op.f("ix_assessment_recommendations_id"), "assessment_recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_assessment_recommendations_parameter_key"), "assessment_recommendations", ["parameter_key"], unique=False)
    op.create_index(op.f("ix_assessment_recommendations_severity"), "assessment_recommendations", ["severity"], unique=False)
    op.create_index(op.f("ix_assessment_recommendations_tenant_id"), "assessment_recommendations", ["tenant_id"], unique=False)
    op.create_index("ix_assessment_recommendations_tenant_created", "assessment_recommendations", ["tenant_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assessment_recommendations_tenant_created", table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_tenant_id"), table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_severity"), table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_parameter_key"), table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_id"), table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_created_at"), table_name="assessment_recommendations")
    op.drop_index("ix_assessment_recommendations_assessment_created", table_name="assessment_recommendations")
    op.drop_index(op.f("ix_assessment_recommendations_assessment_id"), table_name="assessment_recommendations")
    op.drop_table("assessment_recommendations")

    op.drop_index("ix_assessment_events_tenant_created", table_name="assessment_events")
    op.drop_index(op.f("ix_assessment_events_tenant_id"), table_name="assessment_events")
    op.drop_index(op.f("ix_assessment_events_id"), table_name="assessment_events")
    op.drop_index(op.f("ix_assessment_events_event_type"), table_name="assessment_events")
    op.drop_index(op.f("ix_assessment_events_created_at"), table_name="assessment_events")
    op.drop_index("ix_assessment_events_assessment_created", table_name="assessment_events")
    op.drop_index(op.f("ix_assessment_events_assessment_id"), table_name="assessment_events")
    op.drop_table("assessment_events")

    op.drop_index("ix_assessment_jobs_tenant_status", table_name="assessment_jobs")
    op.drop_index(op.f("ix_assessment_jobs_tenant_id"), table_name="assessment_jobs")
    op.drop_index(op.f("ix_assessment_jobs_status"), table_name="assessment_jobs")
    op.drop_index(op.f("ix_assessment_jobs_id"), table_name="assessment_jobs")
    op.drop_index(op.f("ix_assessment_jobs_created_at"), table_name="assessment_jobs")
    op.drop_index("ix_assessment_jobs_assessment_created", table_name="assessment_jobs")
    op.drop_index(op.f("ix_assessment_jobs_assessment_id"), table_name="assessment_jobs")
    op.drop_table("assessment_jobs")
