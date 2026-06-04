"""
Central import point for all models so Alembic can detect metadata.
"""

from app.db.models.base_model import Base

# Import all models here for Alembic
from app.db.models.user import User
from app.db.models.tenant import ConnectedTenant
from app.db.models.user_session import UserSession
from app.db.models.refresh_token import RefreshToken
from app.db.models.audit_log import AuditLog
from app.db.models.assessment import Assessment
from app.db.models.assessment_finding import AssessmentFinding
from app.db.models.assessment_job import AssessmentJob
from app.db.models.assessment_event import AssessmentEvent
from app.db.models.assessment_parameter import AssessmentParameter
from app.db.models.assessment_recommendation import AssessmentRecommendation
from app.db.models.assessment_rule import AssessmentRule
from app.db.models.assessment_report import AssessmentReport
from app.db.models.assessment_artifact import AssessmentArtifact
from app.db.models.cra_parameter import (
    CraAssessmentResult,
    CraParameter,
    CraParameterEvidence,
    CraParameterVersion,
)
