"""
CRA Backend — Microsoft Entra ID authentication + CRA JWT.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1 import health as health_api
from app.api.v1 import websocket as websocket_api
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware
from app.db.session import engine
from app.services.graph_app_registration_service import GRAPH_APP_REGISTRATION_SERVICE_VERSION
from app.services.tenant_deployment_service import DEPLOYMENT_SERVICE_VERSION
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("DEPLOYMENT_SERVICE_VERSION=%s", DEPLOYMENT_SERVICE_VERSION)
    logger.info("GRAPH_APP_REGISTRATION_SERVICE_VERSION=%s", GRAPH_APP_REGISTRATION_SERVICE_VERSION)
    yield
    await engine.dispose()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Copilot Readiness Assessment (CRA) API.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_middleware(app)
register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(health_api.router)
app.include_router(websocket_api.router)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "CRA JWT from POST /api/v1/auth/login",
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/", tags=["Root"])
def home() -> dict[str, Any]:
    logger.info("Home route accessed")
    return {
        "message": f"{settings.app_name} Running Successfully",
        "version": settings.app_version,
    }
