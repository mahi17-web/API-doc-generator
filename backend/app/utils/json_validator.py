"""
utils/json_validator.py - JSON extraction and OpenAPI validation helpers.
"""

import json
import re
from typing import Optional, Dict, Any

from app.core.logger import logger


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of a JSON object from potentially noisy LLM output.

    Strategies tried in order:
      1. Direct json.loads on the full text
      2. Extract from markdown code fences
      3. Slice from first '{' to last '}'
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: markdown fence
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: outermost braces
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("JSON extraction failed; first 300 chars: %s", text[:300])
    return None


def validate_openapi(spec: Dict[str, Any]) -> list[str]:
    """
    Validate minimum OpenAPI 3.0 structure.
    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []

    # Auto-repair openapi version
    if "openapi" not in spec:
        spec["openapi"] = "3.0.0"
        logger.warning("openapi validation: missing 'openapi' field, auto-injected '3.0.0'")

    # Auto-repair info object
    info = spec.get("info")
    if not isinstance(info, dict):
        info = {}
        spec["info"] = info
        logger.warning("openapi validation: missing 'info' object, auto-injected defaults")
    
    if "title" not in info:
        info["title"] = "Generated API"
    if "version" not in info:
        info["version"] = "1.0.0"

    paths = spec.get("paths")
    if not isinstance(paths, dict) or len(paths) == 0:
        errors.append("'paths' is empty or missing")

    if errors:
        for e in errors:
            logger.warning("openapi validation: %s", e)
    else:
        logger.info("openapi validation passed with %d paths", len(spec.get("paths", {})))

    return errors
