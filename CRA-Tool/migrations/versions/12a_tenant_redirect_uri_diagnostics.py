"""tenant redirect uri diagnostics

Revision ID: 12a_tenant_redirect_uri_diagnostics
Revises: 11a_repair_tenant_deployment_schema
Create Date: 2026-05-29 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "12a_tenant_redirect_uri_diagnostics"
down_revision: Union[str, Sequence[str], None] = "11a_repair_tenant_deployment_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}
    if "redirect_uri" not in existing:
        op.add_column("connected_tenants", sa.Column("redirect_uri", sa.String(length=1000), nullable=True))
    if "deployment_diagnostics" not in existing:
        op.add_column("connected_tenants", sa.Column("deployment_diagnostics", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("connected_tenants")}
    if "deployment_diagnostics" in existing:
        op.drop_column("connected_tenants", "deployment_diagnostics")
    if "redirect_uri" in existing:
        op.drop_column("connected_tenants", "redirect_uri")
