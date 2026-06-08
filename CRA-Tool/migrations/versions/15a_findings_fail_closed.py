"""Migrate findings to fail-closed: licensing_required/skipped/manual_validation → fail

Revision ID: 15a_findings_fail_closed
Revises: 14a_assessment_artifact_evidence_fields
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "15a_findings_fail_closed"
down_revision: Union[str, Sequence[str], None] = "14a_assessment_artifact_evidence_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE assessment_findings
            SET status = 'fail'
            WHERE status IN ('licensing_required', 'skipped', 'manual_validation', 'manual_validation_required')
            """
        )
    )


def downgrade() -> None:
    pass
