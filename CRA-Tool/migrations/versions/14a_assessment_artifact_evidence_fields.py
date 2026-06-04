"""assessment artifact evidence fields

Revision ID: 14a_assessment_artifact_evidence_fields
Revises: 13a_cra_parameter_engine_foundation
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "14a_assessment_artifact_evidence_fields"
down_revision: Union[str, Sequence[str], None] = "13a_cra_parameter_engine_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_column(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column("assessment_artifacts", sa.Column("parameter_name", sa.String(length=500), nullable=True))
    _add_column("assessment_artifacts", sa.Column("collector_name", sa.String(length=255), nullable=True))
    _add_column("assessment_artifacts", sa.Column("graph_endpoint", sa.String(length=1000), nullable=True))
    _add_column("assessment_artifacts", sa.Column("actual_value", sa.JSON(), nullable=True))
    _add_column("assessment_artifacts", sa.Column("expected_value", sa.String(length=1000), nullable=True))
    _add_column("assessment_artifacts", sa.Column("raw_evidence_json", sa.JSON(), nullable=True))
    _add_column("assessment_artifacts", sa.Column("collection_timestamp", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    existing = _columns("assessment_artifacts")
    for column_name in [
        "collection_timestamp",
        "raw_evidence_json",
        "expected_value",
        "actual_value",
        "graph_endpoint",
        "collector_name",
        "parameter_name",
    ]:
        if column_name in existing:
            op.drop_column("assessment_artifacts", column_name)
