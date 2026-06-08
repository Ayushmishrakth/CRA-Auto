"""Merge heads: 10_add_assessment_deleted_at and 15a_findings_fail_closed

Revision ID: 16a_merge_heads
Revises: 10_add_assessment_deleted_at, 15a_findings_fail_closed
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

revision: str = "16a_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "10_add_assessment_deleted_at",
    "15a_findings_fail_closed",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
