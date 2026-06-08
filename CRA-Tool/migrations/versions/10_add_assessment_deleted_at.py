"""add deleted_at to assessments

Revision ID: 10_add_assessment_deleted_at
Revises: 9a_assessment_artifacts
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "10_add_assessment_deleted_at"
down_revision: Union[str, Sequence[str], None] = "14a_assessment_artifact_evidence_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "deleted_at")
