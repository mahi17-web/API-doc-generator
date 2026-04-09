"""
api/routes.py - FastAPI endpoint definitions.
"""

import os
import traceback
from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import logger
from app.models.request_models import GenerateDocsRequest
from app.models.response_models import (
    HealthResponse,
    GenerateDocsResponse,
    ErrorResponse,
)
from app.services.openapi_service import generate as generate_spec
from app.services.sdk_service import generate_all

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
def health_check():
    """Returns service health status."""
    return HealthResponse(status="ok")


@router.post(
    "/generate-docs",
    response_model=GenerateDocsResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Generate API documentation and SDKs",
    tags=["Generation"],
)
def generate_docs(body: GenerateDocsRequest):
    """
    Accepts a backend file path, runs the full pipeline:
    parse -> Ollama LLM -> validate -> save spec -> generate SDKs.
    """
    filepath = body.file_path

    # Validate file exists
    if not os.path.isfile(filepath):
        logger.warning("file not found: %s", filepath)
        return GenerateDocsResponse(
            success=False,
            message=f"File not found: {filepath}",
        )

    try:
        logger.info("pipeline triggered via API for: %s", filepath)

        # 1. Generate spec
        result = generate_spec(filepath, model=body.model)
        if result is None:
            return GenerateDocsResponse(
                success=False,
                message="Spec generation failed (check logs for details)",
            )

        # 2. Generate SDKs
        sdk_results = generate_all(result["spec_path"])

        logger.info("pipeline complete")

        return GenerateDocsResponse(
            success=True,
            spec_path=result["spec_path"],
            routes_found=result["routes_found"],
            models_found=result["models_found"],
            sdk_results=sdk_results,
            message="Documentation generated successfully",
        )

    except Exception as exc:
        logger.error("pipeline error: %s\n%s", exc, traceback.format_exc())
        return GenerateDocsResponse(
            success=False,
            message=f"Internal error: {str(exc)}",
        )
