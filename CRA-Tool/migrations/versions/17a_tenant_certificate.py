"""tenant per-tenant certificate columns

Revision ID: 17a_tenant_certificate
Revises: 16a_merge_heads
Create Date: 2026-07-01 00:00:00.000000

Adds per-tenant certificate storage used for PowerShell app-only auth
(PnP/Teams/Exchange). PFX bytes + password are stored encrypted at rest.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "17a_tenant_certificate"
down_revision: Union[str, Sequence[str], None] = "16a_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = (
    ("cert_pfx_encrypted", sa.Text()),
    ("cert_pfx_password_encrypted", sa.Text()),
    ("cert_thumbprint", sa.String(length=40)),
    ("cert_der_b64", sa.Text()),
    ("cert_status", sa.String(length=50)),
    ("teams_role_status", sa.String(length=50)),
)


def _existing_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns("connected_tenants")}


def upgrade() -> None:
    existing = _existing_columns()
    for name, coltype in _COLUMNS:
        if name not in existing:
            op.add_column("connected_tenants", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    existing = _existing_columns()
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("connected_tenants", name)
