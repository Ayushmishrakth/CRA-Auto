"""
API v1 router registration.
"""

from fastapi import APIRouter

from app.api.v1 import admin, assessments, auth, health, parameters, registry, reports, tenants

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(assessments.router)
api_router.include_router(reports.router)
api_router.include_router(registry.router)
api_router.include_router(parameters.router)
api_router.include_router(admin.router)
