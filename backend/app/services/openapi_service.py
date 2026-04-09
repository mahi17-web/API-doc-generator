"""
services/openapi_service.py - Validates, backs up, and saves OpenAPI specs.

Coordinates parser + Ollama to produce a validated spec/api.json.
"""

import json
from typing import Optional, Dict, Any

from app.core.config import settings
from app.core.logger import logger
from app.utils.file_utils import write_file, backup_file
from app.utils.json_validator import validate_openapi
from app.services.parser_service import parse
from app.services.ollama_service import generate_spec


def _save_spec(spec: Dict[str, Any]) -> str:
    """Serialise spec dict to JSON and write to spec_file."""
    content = json.dumps(spec, indent=2, ensure_ascii=False)
    return write_file(settings.spec_file, content)


def generate(filepath: str,
             model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Full pipeline:  parse -> Ollama -> validate -> backup -> save.

    Returns a result dict with:
      spec_path, routes_found, models_found
    or None on failure.
    """
    logger.info("=" * 60)
    logger.info("generating spec from: %s", filepath)
    logger.info("=" * 60)

    # 1. Parse
    parsed = parse(filepath)

    # 2. LLM
    spec = generate_spec(
        source_code=parsed["source_code"],
        routes=parsed["routes"],
        models=parsed["models"],
        model=model,
    )
    if spec is None:
        logger.error("LLM returned no spec")
        return None

    # 3. Validate
    errors = validate_openapi(spec)
    if errors:
        logger.error("spec validation failed (%d errors), NOT saving", len(errors))
        return None

    # 4. Backup + Save
    backup_file(settings.spec_file, settings.backup_dir)
    spec_path = _save_spec(spec)

    logger.info("spec generation complete -> %s", spec_path)

    return {
        "spec_path": spec_path,
        "routes_found": len(parsed["routes"]),
        "models_found": len(parsed["models"]),
    }
