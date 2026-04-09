"""
main.py - Orchestrator for the API Documentation & SDK Generator.

Usage:
  python main.py                            # one-shot generate (default)
  python main.py generate                   # same
  python main.py generate -f myapp.py       # custom backend file
  python main.py watch                      # watch mode
  python main.py parse                      # inspect extracted routes
  python main.py spec                       # generate spec only (no SDK)
  python main.py sdk                        # SDKs from existing spec
"""

import sys
import io
import os
import json
import argparse
from datetime import datetime

# Fix Windows console encoding once at the entry point
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from parser import parse_backend
from generator import generate, SPEC_FILE
from sdk_generator import generate_all
from watcher import watch


BANNER = r"""
  ┌─────────────────────────────────────────┐
  │   API Doc & SDK Generator               │
  │   Powered by Ollama LLM                 │
  └─────────────────────────────────────────┘
"""


def cmd_generate(args):
    """One-shot: parse -> spec -> SDKs."""
    print(f"[main] mode: GENERATE")
    print(f"[main] file:  {args.file}")
    print(f"[main] model: {args.model}")
    print(f"[main] time:  {datetime.now().isoformat()}")

    spec_path = generate(args.file, model=args.model)
    if not spec_path:
        print("\n[main] spec generation FAILED")
        sys.exit(1)

    results = generate_all(spec_path)

    print(f"\n{'=' * 60}")
    print(f"[main] DONE  spec -> {spec_path}")
    for lang, ok in results.items():
        tag = "OK" if ok else "SKIPPED (install openapi-generator-cli)"
        print(f"[main]       sdk/{lang}: {tag}")
    print(f"{'=' * 60}")


def cmd_watch(args):
    """Watch mode: initial generate + continuous monitoring."""
    print(f"[main] mode: WATCH  ({args.file})")

    spec = generate(args.file, model=args.model)
    if spec:
        generate_all(spec)

    watch([args.file], model=args.model)


def cmd_parse(args):
    """Parse only: show what the extractor finds."""
    print(f"[main] mode: PARSE  ({args.file})")
    data = parse_backend(args.file)

    print(f"\nFramework: {data['framework']}")
    print(f"\nRoutes ({len(data['routes'])}):")
    for r in data["routes"]:
        print(f"  {r['method']:7s} {r['path']}")
        if r.get("summary"):
            print(f"          summary:  {r['summary']}")
        if r.get("docstring"):
            print(f"          doc:      {r['docstring']}")
        if r.get("response_model"):
            print(f"          response: {r['response_model']}")

    print(f"\nModels ({len(data['models'])}):")
    for m in data["models"]:
        print(f"  {m['name']}:")
        for f in m["fields"]:
            d = f" = {f['default']}" if f.get("default") else ""
            print(f"    {f['name']}: {f['type']}{d}")


def cmd_spec(args):
    """Generate spec only, no SDKs."""
    print(f"[main] mode: SPEC ONLY")
    path = generate(args.file, model=args.model)
    if path:
        with open(path) as fh:
            preview = json.dumps(json.load(fh), indent=2)[:2000]
        print(f"\n{preview}")
    else:
        print("[main] spec generation FAILED")
        sys.exit(1)


def cmd_sdk(args):
    """SDKs from existing spec."""
    spec = args.spec or SPEC_FILE
    if not os.path.isfile(spec):
        print(f"[main] spec not found: {spec}")
        print("[main] run 'python main.py spec' first")
        sys.exit(1)
    print(f"[main] mode: SDK ONLY  ({spec})")
    generate_all(spec)


def main():
    ap = argparse.ArgumentParser(
        description="API Documentation & SDK Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command")

    def _common(p):
        p.add_argument("-f", "--file", default="sample_backend.py")
        p.add_argument("-m", "--model", default="llama3")

    for name, help_text in [
        ("generate", "One-shot spec + SDK generation"),
        ("watch",    "Watch files and auto-regenerate"),
        ("parse",    "Parse and inspect extracted API info"),
        ("spec",     "Generate OpenAPI spec only"),
    ]:
        _common(sub.add_parser(name, help=help_text))

    sdk_p = sub.add_parser("sdk", help="Generate SDKs from existing spec")
    sdk_p.add_argument("-s", "--spec", default=None)

    args = ap.parse_args()
    print(BANNER)

    dispatch = {
        "generate": cmd_generate,
        "watch":    cmd_watch,
        "parse":    cmd_parse,
        "spec":     cmd_spec,
        "sdk":      cmd_sdk,
        None:       cmd_generate,   # default
    }

    handler = dispatch.get(args.command, cmd_generate)
    if not hasattr(args, "file"):
        args.file = "sample_backend.py"
    if not hasattr(args, "model"):
        args.model = "llama3"
    handler(args)


if __name__ == "__main__":
    main()
