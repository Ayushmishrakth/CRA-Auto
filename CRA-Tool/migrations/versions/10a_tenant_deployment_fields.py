"""tenant deployment fields

Revision ID: 10a_tenant_deployment_fields
Revises: 9a_assessment_artifacts
Create Date: 2026-05-29 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "10a_tenant_deployment_fields"
down_revision: Union[str, Sequence[str], None] = "9a_assessment_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}

    def add_if_missing(column: sa.Column) -> None:
        if column.name not in existing:
            op.add_column("connected_tenants", column)
            existing.add(column.name)

    add_if_missing(sa.Column("application_client_id", sa.String(length=64), nullable=True))
    add_if_missing(sa.Column("application_object_id", sa.String(length=64), nullable=True))
    add_if_missing(sa.Column("service_principal_id", sa.String(length=64), nullable=True))
    if bind.dialect.name != "sqlite":
        op.alter_column("connected_tenants", "encrypted_client_secret", type_=sa.String(length=1000))
    add_if_missing(sa.Column("secret_id", sa.String(length=128), nullable=True))
    add_if_missing(sa.Column("secret_expiration", sa.DateTime(timezone=True), nullable=True))
    add_if_missing(sa.Column("secret_version", sa.String(length=64), nullable=True))
    add_if_missing(sa.Column("deployment_status", sa.String(length=50), nullable=False, server_default="NOT_DEPLOYED"))
    add_if_missing(sa.Column("deployment_step", sa.String(length=80), nullable=True))
    add_if_missing(sa.Column("deployment_timestamp", sa.DateTime(timezone=True), nullable=True))
    add_if_missing(sa.Column("admin_consent_url", sa.String(length=1000), nullable=True))
    add_if_missing(sa.Column("deployment_error", sa.String(length=2000), nullable=True))
    if bind.dialect.name != "sqlite":
        op.alter_column("connected_tenants", "deployment_status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}
    for column_name in [
        "deployment_error",
        "admin_consent_url",
        "deployment_timestamp",
        "deployment_step",
        "deployment_status",
        "secret_version",
        "secret_expiration",
        "secret_id",
        "service_principal_id",
        "application_object_id",
        "application_client_id",
    ]:
        if column_name in existing:
            op.drop_column("connected_tenants", column_name)
    if bind.dialect.name != "sqlite":
        op.alter_column("connected_tenants", "encrypted_client_secret", type_=sa.String(length=255))
