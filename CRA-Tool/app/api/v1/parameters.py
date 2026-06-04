from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.responses import SuccessResponse, success_response
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.parameters import ParameterImportResponse, ParameterVersionResponse
from app.services.cra_parameter_loader_service import import_parameter_workbook, list_parameter_versions


router = APIRouter(prefix="/parameters", tags=["Parameters"])


@router.post("/import", response_model=SuccessResponse[ParameterImportResponse])
async def import_parameters(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SuccessResponse[ParameterImportResponse]:
    content = await file.read()
    result = await import_parameter_workbook(
        db,
        current_user=current_user,
        filename=file.filename or "cra-parameters.xlsx",
        content=content,
        activate=True,
    )
    return success_response(
        message="CRA parameter workbook imported",
        data=ParameterImportResponse(**result),
        request_id=request.state.request_id,
    )


@router.get("/versions", response_model=SuccessResponse[list[ParameterVersionResponse]])
async def get_parameter_versions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> SuccessResponse[list[ParameterVersionResponse]]:
    versions = await list_parameter_versions(db)
    return success_response(
        message="CRA parameter versions retrieved",
        data=[ParameterVersionResponse.model_validate(item) for item in versions],
        request_id=request.state.request_id,
    )
