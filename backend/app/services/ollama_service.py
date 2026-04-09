"""
services/ollama_service.py - All interaction with the Ollama local LLM.

Builds the prompt, calls the HTTP API with retry, and extracts JSON.
"""

import requests
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logger import logger
from app.utils.json_validator import extract_json

# The exact prompt specified in requirements
_SYSTEM_PROMPT = (
    "You are an API documentation generator.\n"
    "Analyze the backend code and return ONLY valid OpenAPI 3.0 JSON.\n"
    "CRITICAL: You MUST use double-quotes around ALL property keys and strings.\n"
    "No explanations. No markdown. Just the raw JSON object.\n"
    "Ensure paths, parameters, requestBody, and responses are included."
)


def _build_prompt(source_code: str,
                  routes_summary: str,
                  models_summary: str) -> str:
    """Assemble the complete generation prompt."""
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"DETECTED ROUTES:\n{routes_summary}\n\n"
        f"DETECTED MODELS:\n{models_summary}\n\n"
        f"FULL SOURCE CODE:\n{source_code}\n\n"
        "Output ONLY the JSON object starting with {{ and ending with }}:"
    )


def _format_routes(routes: List[Dict[str, Any]]) -> str:
    if not routes:
        return "(none detected)"
    lines = []
    for r in routes:
        line = f"  {r['method']:7s} {r['path']}"
        if r.get("summary"):
            line += f"  -- {r['summary']}"
        if r.get("response_model"):
            line += f"  [response: {r['response_model']}]"
        if r.get("docstring"):
            line += f"\n          doc: {r['docstring']}"
        lines.append(line)
    return "\n".join(lines)


def _format_models(models: List[Dict[str, Any]]) -> str:
    if not models:
        return "(none detected)"
    lines = []
    for m in models:
        lines.append(f"  {m['name']}:")
        for f in m["fields"]:
            default = f" = {f['default']}" if f.get("default") else ""
            lines.append(f"    {f['name']}: {f['type']}{default}")
    return "\n".join(lines)


def _call_ollama(prompt: str, model: str) -> Optional[str]:
    """
    POST to Ollama and return the raw response text.
    Retries up to settings.ollama_retries times.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    for attempt in range(1, settings.ollama_retries + 1):
        try:
            logger.info(
                "ollama request -> %s (attempt %d/%d)",
                model, attempt, settings.ollama_retries,
            )
            resp = requests.post(
                settings.ollama_url,
                json=payload,
                timeout=settings.ollama_timeout,
            )
            resp.raise_for_status()

            body = resp.json().get("response", "")
            if not body.strip():
                logger.warning("ollama returned empty response")
                continue

            logger.info("ollama returned %d chars", len(body))
            return body

        except requests.exceptions.ConnectionError:
            logger.error("cannot connect to Ollama at %s", settings.ollama_url)
        except requests.exceptions.Timeout:
            logger.error("ollama timed out after %ds", settings.ollama_timeout)
        except requests.exceptions.RequestException as exc:
            logger.error("ollama request error: %s", exc)

        if attempt < settings.ollama_retries:
            logger.info("retrying ...")

    return None


def generate_spec(source_code: str,
                  routes: List[Dict[str, Any]],
                  models: List[Dict[str, Any]],
                  model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    High-level entry point:
      build prompt -> call Ollama -> extract JSON -> return spec dict.
    """
    model = model or settings.ollama_model
    prompt = _build_prompt(
        source_code,
        _format_routes(routes),
        _format_models(models),
    )

    raw = _call_ollama(prompt, model)
    if raw is None:
        logger.error("no response from Ollama")
        return None

    spec = extract_json(raw)
    if spec is None:
        logger.error("could not extract valid JSON from Ollama response")
        return None

    logger.info("OpenAPI spec extracted successfully")
    return spec
