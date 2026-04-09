"""
models/response_models.py - Pydantic models for API responses.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional


class HealthResponse(BaseModel):
    status: str = "ok"


class GenerateDocsResponse(BaseModel):
    """Response from POST /generate-docs."""
    success: bool
    spec_path: Optional[str] = None
    routes_found: int = 0
    models_found: int = 0
    sdk_results: Dict[str, bool] = Field(default_factory=dict)
    message: str = ""


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
