"""
Report customization schemas for white-label reports.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ReportCustomization(BaseModel):
    """Report customization settings."""

    company_name: Optional[str] = Field(
        default=None,
        description="Custom company name for report branding"
    )
    company_address: Optional[str] = Field(
        default=None,
        description="Custom company address for report"
    )
    logo_path: Optional[str] = Field(
        default=None,
        description="Path to uploaded company logo file"
    )
    report_format: str = Field(
        default="docx",
        pattern="^(docx|pdf|both)$",
        description="Report format: docx, pdf, or both"
    )
    include_logo: bool = Field(
        default=False,
        description="Whether to include uploaded logo in report"
    )


class ReportCustomizationResponse(BaseModel):
    """Response after customization is saved."""

    success: bool
    message: str
    customization_id: Optional[str] = None


class ReportGenerationRequest(BaseModel):
    """Request to generate report with customization."""

    assessment_id: str
    customization: Optional[ReportCustomization] = None
    report_format: str = Field(
        default="docx",
        pattern="^(docx|pdf|both)$"
    )
