"""
services/parser_service.py - Extracts API routes and Pydantic models from
backend source files using regex-based static analysis.
"""

import re
from typing import Dict, Any, List

from app.core.logger import logger
from app.utils.file_utils import read_file


def _re_first(pattern: str, text: str) -> str:
    """Return first capture group or empty string."""
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def _extract_routes(code: str) -> List[Dict[str, Any]]:
    """Extract FastAPI route decorators and their function metadata."""
    dec_re = re.compile(
        r'@\w+\.(get|post|put|patch|delete|options|head)\s*\('
        r'\s*"([^"]+)"'
        r'([^)]*)\)',
        re.IGNORECASE,
    )
    lines = code.split("\n")
    routes: List[Dict[str, Any]] = []
    i = 0

    while i < len(lines):
        m = dec_re.search(lines[i])
        if not m:
            i += 1
            continue

        method = m.group(1).upper()
        path = m.group(2)
        kwargs = m.group(3)

        summary = _re_first(r'summary\s*=\s*"([^"]*)"', kwargs)
        resp_model = _re_first(r'response_model\s*=\s*([\w\[\], ]+)', kwargs)
        status_code = int(_re_first(r'status_code\s*=\s*(\d+)', kwargs) or 200)

        # Advance to the def line
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("def "):
            j += 1

        func_name = ""
        docstring = ""
        body_lines: List[str] = []

        if j < len(lines):
            fn = re.search(r"def\s+(\w+)", lines[j])
            func_name = fn.group(1) if fn else ""

            body_lines.append(lines[j])
            k = j + 1
            while k < len(lines) and (lines[k].strip() == "" or lines[k][:1] in (" ", "\t")):
                body_lines.append(lines[k])
                k += 1

            body = "\n".join(body_lines)
            doc = re.search(r'"""(.*?)"""', body, re.DOTALL) or \
                  re.search(r"'''(.*?)'''", body, re.DOTALL)
            docstring = doc.group(1).strip() if doc else ""
            i = k
        else:
            i = j + 1

        routes.append({
            "method": method,
            "path": path,
            "function_name": func_name,
            "summary": summary,
            "docstring": docstring,
            "response_model": resp_model,
            "status_code": status_code,
            "body": "\n".join(body_lines),
        })

    return routes


def _extract_models(code: str) -> List[Dict[str, Any]]:
    """Extract Pydantic BaseModel subclasses and their typed fields."""
    models: List[Dict[str, Any]] = []
    lines = code.split("\n")
    i = 0

    while i < len(lines):
        cls = re.match(r"class\s+(\w+)\s*\(\s*BaseModel\s*\)\s*:", lines[i].strip())
        if not cls:
            i += 1
            continue

        name = cls.group(1)
        fields: List[Dict[str, Any]] = []
        j = i + 1
        while j < len(lines) and (lines[j].strip() == "" or lines[j][:1] in (" ", "\t")):
            fm = re.match(r"\s+(\w+)\s*:\s*(.+?)(?:\s*=\s*(.+))?\s*$", lines[j])
            if fm:
                fields.append({
                    "name": fm.group(1),
                    "type": fm.group(2).strip(),
                    "default": fm.group(3).strip() if fm.group(3) else None,
                })
            j += 1

        models.append({"name": name, "fields": fields})
        i = j

    return models


def parse(filepath: str) -> Dict[str, Any]:
    """
    Parse a backend source file and return structured metadata.

    Returns dict with keys:
      filepath, framework, source_code, routes, models
    """
    code = read_file(filepath)

    framework = "unknown"
    if "FastAPI" in code or "from fastapi" in code:
        framework = "fastapi"
    elif "Flask" in code or "from flask" in code:
        framework = "flask"

    routes = _extract_routes(code) if framework == "fastapi" else []
    models = _extract_models(code) if framework == "fastapi" else []

    logger.info(
        "parsed %s: framework=%s, %d route(s), %d model(s)",
        filepath, framework, len(routes), len(models),
    )

    return {
        "filepath": filepath,
        "framework": framework,
        "source_code": code,
        "routes": routes,
        "models": models,
    }
