"""
parser.py - Reads backend source files and extracts API metadata via regex.
No imports of the target code are needed; works purely on text.
"""

import os
import re
from typing import Dict, Any, List


def read_file(filepath: str) -> str:
    """Read a source file and return its contents as a string."""
    abs_path = os.path.abspath(filepath)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")
    with open(abs_path, "r", encoding="utf-8") as fh:
        return fh.read()


def detect_framework(code: str) -> str:
    """Return the detected framework name based on import patterns."""
    if "FastAPI" in code or "from fastapi" in code:
        return "fastapi"
    if "Flask" in code or "from flask" in code:
        return "flask"
    return "unknown"


def extract_routes(code: str) -> List[Dict[str, Any]]:
    """
    Extract HTTP route decorators and their associated function signatures
    from FastAPI source code.

    Each result contains: method, path, function_name, summary, docstring,
    response_model, status_code, and the raw function body.
    """
    decorator_re = re.compile(
        r'@\w+\.(get|post|put|patch|delete|options|head)\s*\('
        r'\s*"([^"]+)"'   # path
        r'([^)]*)\)',      # remaining kwargs
        re.IGNORECASE,
    )

    lines = code.split("\n")
    routes: List[Dict[str, Any]] = []
    i = 0

    while i < len(lines):
        m = decorator_re.search(lines[i])
        if not m:
            i += 1
            continue

        method = m.group(1).upper()
        path = m.group(2)
        kwargs_str = m.group(3)

        # Extract decorator metadata
        summary = _re_extract(r'summary\s*=\s*"([^"]*)"', kwargs_str)
        resp_model = _re_extract(r'response_model\s*=\s*([\w\[\], ]+)', kwargs_str)
        status_code = int(_re_extract(r'status_code\s*=\s*(\d+)', kwargs_str) or 200)

        # Find the function def that follows
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("def "):
            j += 1

        func_name = ""
        docstring = ""
        body_lines: List[str] = []

        if j < len(lines):
            fn_match = re.search(r"def\s+(\w+)", lines[j])
            func_name = fn_match.group(1) if fn_match else ""

            # Collect the indented function body
            body_lines.append(lines[j])
            k = j + 1
            while k < len(lines) and (lines[k].strip() == "" or lines[k][:1] in (" ", "\t")):
                body_lines.append(lines[k])
                k += 1

            body_text = "\n".join(body_lines)
            doc_m = re.search(r'"""(.*?)"""', body_text, re.DOTALL) or \
                    re.search(r"'''(.*?)'''", body_text, re.DOTALL)
            docstring = doc_m.group(1).strip() if doc_m else ""
            i = k
        else:
            i = j

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


def extract_models(code: str) -> List[Dict[str, Any]]:
    """Extract Pydantic BaseModel subclasses and their fields."""
    models: List[Dict[str, Any]] = []
    lines = code.split("\n")
    i = 0

    while i < len(lines):
        cls_m = re.match(r"class\s+(\w+)\s*\(\s*BaseModel\s*\)\s*:", lines[i].strip())
        if not cls_m:
            i += 1
            continue

        name = cls_m.group(1)
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


def parse_backend(filepath: str) -> Dict[str, Any]:
    """
    Main entry point.  Returns a dict with:
      filepath, framework, source_code, routes, models
    """
    code = read_file(filepath)
    framework = detect_framework(code)
    routes = extract_routes(code) if framework == "fastapi" else []
    models = extract_models(code) if framework == "fastapi" else []

    print(f"[parser] {filepath}: framework={framework}, "
          f"{len(routes)} route(s), {len(models)} model(s)")
    return {
        "filepath": filepath,
        "framework": framework,
        "source_code": code,
        "routes": routes,
        "models": models,
    }


# ---- helpers ----------------------------------------------------------------

def _re_extract(pattern: str, text: str) -> str:
    """Return first capture group or empty string."""
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_backend.py"
    info = parse_backend(target)
    for r in info["routes"]:
        print(f"  {r['method']:7s} {r['path']:<30s} -> {r['function_name']}()")
    for m in info["models"]:
        flds = ", ".join(f["name"] for f in m["fields"])
        print(f"  model {m['name']}: {flds}")
