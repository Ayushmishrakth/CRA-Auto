"""
Temporary storage for report customization data (logo, address, company_name) during report generation.
"""

from uuid import UUID
from typing import Optional, Dict, Any

# In-memory storage for assessment customization (cleared after report generation)
_customization_cache: Dict[str, Dict[str, Any]] = {}


def store_customization(
    assessment_id: UUID,
    logo_path: Optional[str] = None,
    address: Optional[str] = None,
    company_name: Optional[str] = None,
    output_format: Optional[str] = None,
) -> None:
    """Store logo, address, and company_name temporarily for this assessment."""
    import logging
    logger = logging.getLogger(__name__)

    key = str(assessment_id)
    _customization_cache[key] = {
        "logo_path": logo_path,
        "address": address,
        "company_name": company_name,
        "output_format": output_format or "docx",
    }

    logger.info(f"[CACHE] Storing customization for {assessment_id}:")
    logger.info(f"[CACHE]   logo_path: {logo_path}")
    logger.info(f"[CACHE]   company_name: {company_name}")
    logger.info(f"[CACHE]   address: {address}")
    logger.info(f"[CACHE] Cache size: {len(_customization_cache)}")


def get_customization(assessment_id: UUID) -> Dict[str, Any]:
    """Retrieve stored customization for an assessment."""
    key = str(assessment_id)
    return _customization_cache.get(key, {
        "logo_path": None,
        "address": None,
        "company_name": None,
    })


def clear_customization(assessment_id: UUID) -> None:
    """Clear customization after report generation."""
    key = str(assessment_id)
    _customization_cache.pop(key, None)


def get_customization_for_pdf(assessment_id: UUID) -> Dict[str, Any]:
    """Get customization data formatted for PDF renderer."""
    import logging
    from pathlib import Path
    logger = logging.getLogger(__name__)

    customization = get_customization(assessment_id)

    logger.info(f"[CACHE] Retrieving customization for {assessment_id}:")
    logger.info(f"[CACHE]   logo_path from cache: {customization.get('logo_path')}")
    logger.info(f"[CACHE]   company_name from cache: {customization.get('company_name')}")
    logger.info(f"[CACHE]   address from cache: {customization.get('address')}")

    if customization.get("logo_path"):
        path = Path(customization.get("logo_path"))
        logger.info(f"[CACHE]   logo file exists: {path.exists()}")
        if path.exists():
            logger.info(f"[CACHE]   logo file size: {path.stat().st_size} bytes")

    return {
        "logo_path": customization.get("logo_path"),
        "address": customization.get("address"),
        "company_name": customization.get("company_name"),
        "output_format": customization.get("output_format") or "docx",
    }
