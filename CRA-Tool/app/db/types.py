"""
Database type helpers shared by ORM models.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


JSONType = JSON().with_variant(JSONB(), "postgresql")
