"""
sdk_generator.py - Generates Python and JavaScript client SDKs
from an OpenAPI spec using openapi-generator-cli.
Auto-detects npm / npx / docker availability.
"""

import os
import subprocess
from typing import List, Dict

SPEC_FILE = os.path.join("spec", "api.json")
SDK_DIR = "sdk"
LANGUAGES = ["python", "javascript"]


# ---- tooling detection -------------------------------------------------------

def _find_generator() -> str:
    """
    Check which openapi-generator method is available.
    Returns one of: 'npm', 'npx', 'docker', 'none'.
    """
    for label, cmd in [
        ("npm", ["openapi-generator-cli", "version"]),
        ("npx", ["npx", "@openapitools/openapi-generator-cli", "version"]),
        ("docker", ["docker", "version"]),
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                print(f"[sdk] found generator via {label}")
                return label
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    print("[sdk] WARNING: openapi-generator-cli not found")
    print("[sdk] install with:  npm i @openapitools/openapi-generator-cli -g")
    return "none"


def _build_cmd(method: str, lang: str, spec: str, outdir: str) -> List[str]:
    """Return the CLI command list for the chosen generator method."""
    spec_abs = os.path.abspath(spec)
    out_abs = os.path.abspath(outdir)
    common = ["-i", spec_abs, "-g", lang, "-o", out_abs, "--skip-validate-spec"]

    if method == "npm":
        return ["openapi-generator-cli", "generate"] + common
    if method == "npx":
        return ["npx", "@openapitools/openapi-generator-cli", "generate"] + common
    if method == "docker":
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


# ---- public API --------------------------------------------------------------

def generate_sdk(lang: str, spec: str = SPEC_FILE) -> bool:
    """Generate a single SDK. Returns True on success."""
    if not os.path.isfile(spec):
        print(f"[sdk] spec not found: {spec}")
        return False

    outdir = os.path.join(SDK_DIR, lang)
    os.makedirs(outdir, exist_ok=True)

    method = _find_generator()
    if method == "none":
        print(f"[sdk] skipping {lang} (no generator)")
        print(f"[sdk] manual:  openapi-generator-cli generate -i {spec} -g {lang} -o {outdir}")
        return False

    cmd = _build_cmd(method, lang, spec, outdir)
    print(f"[sdk] generating {lang} SDK ...")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            print(f"[sdk] OK -> {outdir}")
            return True
        print(f"[sdk] FAIL (exit {r.returncode})")
        if r.stderr:
            for line in r.stderr.strip().splitlines()[-5:]:
                print(f"[sdk]   {line}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[sdk] timed out for {lang}")
        return False
    except Exception as exc:
        print(f"[sdk] error: {exc}")
        return False


def generate_all(spec: str = SPEC_FILE) -> Dict[str, bool]:
    """Generate SDKs for every language in LANGUAGES."""
    print(f"\n{'=' * 60}")
    print(f"[sdk] generating SDKs: {', '.join(LANGUAGES)}")
    print(f"{'=' * 60}")

    results = {}
    for lang in LANGUAGES:
        results[lang] = generate_sdk(lang, spec)

    print("\n[sdk] summary:")
    for lang, ok in results.items():
        print(f"  {lang:15s} {'OK' if ok else 'SKIPPED'}")
    return results


if __name__ == "__main__":
    import sys
    generate_all(sys.argv[1] if len(sys.argv) > 1 else SPEC_FILE)
