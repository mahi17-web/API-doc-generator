"""
models/request_models.py - Pydantic models for incoming API requests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class GenerateDocsRequest(BaseModel):
    """Body for POST /generate-docs."""
    file_path: str = Field(
        ...,
        description="Path to the backend source file to analyse",
        examples=["sample_backend/app.py"],
    )
    model: Optional[str] = Field(
        default=None,
        description="Override the default Ollama model",
    )
