"""
services/sdk_service.py - Generates client SDKs from an OpenAPI spec
using openapi-generator-cli (npm global, npx, or Docker).
"""

import os
import subprocess
from typing import Dict, List

from app.core.config import settings
from app.core.logger import logger


def _detect_tool() -> str:
    """
    Find which openapi-generator method is available.
    Returns: 'npm' | 'npx' | 'docker' | 'none'
    """
    checks = [
        ("npm", ["openapi-generator-cli", "version"]),
        ("npx", ["npx", "@openapitools/openapi-generator-cli", "version"]),
        ("docker", ["docker", "version"]),
    ]
    for label, cmd in checks:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                logger.info("sdk tool detected: %s", label)
                return label
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    logger.warning("no openapi-generator-cli found")
    return "none"


def _build_cmd(tool: str, lang: str, spec: str, outdir: str) -> List[str]:
    """Construct the CLI command list."""
    spec_abs = os.path.abspath(spec)
    out_abs = os.path.abspath(outdir)
    common = ["-i", spec_abs, "-g", lang, "-o", out_abs, "--skip-validate-spec"]

    if tool == "npm":
        return ["openapi-generator-cli", "generate"] + common
    if tool == "npx":
        return ["npx", "@openapitools/openapi-generator-cli", "generate"] + common
    if tool == "docker":
        spec_dir = os.path.dirname(spec_abs)
        spec_name = os.path.basename(spec_abs)
        return [
            "docker", "run", "--rm",
            "-v", f"{spec_dir}:/spec",
            "-v", f"{out_abs}:/out",
            "openapitools/openapi-generator-cli", "generate",
            "-i", f"/spec/{spec_name}", "-g", lang, "-o", "/out",
            "--skip-validate-spec",
        ]
    return []


def generate_sdk(lang: str, spec_path: str = "") -> bool:
    """Generate a single language SDK. Returns True on success."""
    spec = spec_path or settings.spec_file
    if not os.path.isfile(spec):
        logger.error("spec not found: %s", spec)
        return False

    outdir = os.path.join(settings.sdk_dir, lang)
    os.makedirs(outdir, exist_ok=True)

    tool = _detect_tool()
    if tool == "none":
        logger.info(
            "skipping %s SDK; install with: npm i @openapitools/openapi-generator-cli -g", lang
        )
        logger.info(
            "manual: openapi-generator-cli generate -i %s -g %s -o %s", spec, lang, outdir
        )
        return False

    cmd = _build_cmd(tool, lang, spec, outdir)
    logger.info("generating %s SDK ...", lang)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            logger.info("%s SDK generated -> %s", lang, outdir)
            return True
        logger.error("%s SDK failed (exit %d)", lang, r.returncode)
        if r.stderr:
            for line in r.stderr.strip().splitlines()[-5:]:
                logger.error("  %s", line)
        return False
    except subprocess.TimeoutExpired:
        logger.error("%s SDK generation timed out", lang)
        return False
    except Exception as exc:
        logger.error("sdk error: %s", exc)
        return False


def generate_all(spec_path: str = "") -> Dict[str, bool]:
    """Generate SDKs for all configured languages."""
    spec = spec_path or settings.spec_file
    logger.info("generating SDKs: %s", ", ".join(settings.sdk_languages))

    results: Dict[str, bool] = {}
    for lang in settings.sdk_languages:
        results[lang] = generate_sdk(lang, spec)

    for lang, ok in results.items():
        logger.info("  %s: %s", lang, "OK" if ok else "SKIPPED")
    return results
