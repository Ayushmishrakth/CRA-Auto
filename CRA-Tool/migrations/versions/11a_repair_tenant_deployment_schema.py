"""repair tenant deployment schema

Revision ID: 11a_repair_tenant_deployment_schema
Revises: 10a_tenant_deployment_fields
Create Date: 2026-05-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "11a_repair_tenant_deployment_schema"
down_revision: Union[str, Sequence[str], None] = "10a_tenant_deployment_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _copy_if_possible(bind, source: str, target: str) -> None:
    columns = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}
    if source in columns and target in columns:
        op.execute(sa.text(f"UPDATE connected_tenants SET {target} = {source} WHERE {target} IS NULL"))


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
    add_if_missing(sa.Column("secret_id", sa.String(length=128), nullable=True))
    add_if_missing(sa.Column("secret_expiration", sa.DateTime(timezone=True), nullable=True))
    add_if_missing(sa.Column("secret_version", sa.String(length=64), nullable=True))
    add_if_missing(sa.Column("deployment_status", sa.String(length=50), nullable=False, server_default="NOT_DEPLOYED"))
    add_if_missing(sa.Column("deployment_step", sa.String(length=80), nullable=True))
    add_if_missing(sa.Column("deployment_timestamp", sa.DateTime(timezone=True), nullable=True))
    add_if_missing(sa.Column("admin_consent_url", sa.String(length=1000), nullable=True))
    add_if_missing(sa.Column("deployment_error", sa.String(length=2000), nullable=True))

    _copy_if_possible(bind, "app_client_id", "application_client_id")
    _copy_if_possible(bind, "app_registration_id", "application_object_id")
    _copy_if_possible(bind, "secret_expires_at", "secret_expiration")

    if "deployment_status" in existing:
        op.execute(
            sa.text(
                "UPDATE connected_tenants "
                "SET deployment_status = 'NOT_DEPLOYED' "
                "WHERE deployment_status IS NULL OR deployment_status = 'not_started'"
            )
        )

    if "status" in existing:
        op.execute(
            sa.text(
                "UPDATE connected_tenants "
                "SET status = 'NOT_DEPLOYED' "
                "WHERE status IS NULL OR status IN ('pending', 'active', 'disconnected')"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}
    for column_name in [
        "deployment_timestamp",
        "deployment_step",
        "secret_expiration",
        "secret_id",
        "application_object_id",
        "application_client_id",
    ]:
        if column_name in existing:
            op.drop_column("connected_tenants", column_name)
