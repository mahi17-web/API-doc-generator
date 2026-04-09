"""
generator.py - Validates LLM output, backs up existing specs, and writes spec/api.json.
Never overwrites a valid spec with invalid data.
"""

import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, Any

from parser import parse_backend
from ollama_api import generate_openapi

SPEC_DIR = "spec"
SPEC_FILE = os.path.join(SPEC_DIR, "api.json")
BACKUP_DIR = os.path.join(SPEC_DIR, "backups")


# ---- validation -------------------------------------------------------------

def validate_spec(spec: Dict[str, Any]) -> bool:
    """Return True when the spec has the minimum required OpenAPI fields."""
    errors = []
    if "openapi" not in spec:
        errors.append("missing 'openapi' version")
    info = spec.get("info")
    if not isinstance(info, dict) or "title" not in info or "version" not in info:
        errors.append("missing or incomplete 'info'")
    paths = spec.get("paths")
    if not isinstance(paths, dict) or len(paths) == 0:
        errors.append("'paths' is empty or missing")
    if errors:
        for e in errors:
            print(f"[generator] validation FAIL: {e}")
        return False
    print(f"[generator] validation OK  ({len(paths)} path(s))")
    return True


# ---- file I/O ---------------------------------------------------------------

def _backup_existing() -> Optional[str]:
    """Copy current spec to a timestamped backup if it exists."""
    if not os.path.isfile(SPEC_FILE):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"api_{ts}.json")
    shutil.copy2(SPEC_FILE, dst)
    print(f"[generator] backed up -> {dst}")
    return dst


def save_spec(spec: Dict[str, Any]) -> str:
    """Write the spec dict to SPEC_FILE as pretty-printed JSON."""
    os.makedirs(SPEC_DIR, exist_ok=True)
    with open(SPEC_FILE, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)
    print(f"[generator] saved -> {SPEC_FILE}")
    return SPEC_FILE


# ---- pipeline ---------------------------------------------------------------

def generate(filepath: str, model: str = "llama3") -> Optional[str]:
    """
    Full pipeline:
      parse backend -> call LLM -> validate -> backup -> save.
    Returns the path to the saved spec or None on failure.
    """
    print(f"\n{'=' * 60}")
    print(f"[generator] generating spec from: {filepath}")
    print(f"{'=' * 60}\n")

    parsed = parse_backend(filepath)

    spec = generate_openapi(
        source_code=parsed["source_code"],
        routes=parsed["routes"],
        models=parsed["models"],
        model=model,
    )
    if spec is None:
        print("[generator] FAILED: no spec returned by LLM")
        return None

    if not validate_spec(spec):
        print("[generator] FAILED: spec invalid, existing file preserved")
        return None

    _backup_existing()
    return save_spec(spec)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_backend.py"
    result = generate(target)
    print(f"\nResult: {result or 'FAILED'}")
