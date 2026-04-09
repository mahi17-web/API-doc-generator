"""
ollama_api.py - Sends prompts to Ollama, extracts clean JSON from the response.
Handles timeouts, retries, and messy LLM output.
"""

import json
import re
import requests
from typing import Optional, Dict, Any, List

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"
TIMEOUT = 300  # seconds


# ---- prompt construction ----------------------------------------------------

SYSTEM_INSTRUCTION = (
    "You are an API documentation generator.\n"
    "Analyze the given backend code and return ONLY valid OpenAPI 3.0 JSON.\n"
    "No explanations. No markdown.\n"
    "Ensure paths, parameters, requestBody, and responses are included."
)


def build_prompt(source_code: str,
                 routes_summary: str,
                 models_summary: str) -> str:
    """Assemble the full prompt sent to the LLM."""
    return (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"DETECTED ROUTES:\n{routes_summary}\n\n"
        f"DETECTED MODELS:\n{models_summary}\n\n"
        f"FULL SOURCE CODE:\n{source_code}\n\n"
        "Output ONLY the JSON object starting with { and ending with }:"
    )


def format_routes(routes: List[Dict[str, Any]]) -> str:
    """Human-readable route list for the prompt."""
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


def format_models(models: List[Dict[str, Any]]) -> str:
    """Human-readable model list for the prompt."""
    if not models:
        return "(none detected)"
    lines = []
    for m in models:
        lines.append(f"  {m['name']}:")
        for f in m["fields"]:
            default = f" = {f['default']}" if f.get("default") else ""
            lines.append(f"    {f['name']}: {f['type']}{default}")
    return "\n".join(lines)


# ---- JSON extraction --------------------------------------------------------

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of a JSON object from potentially noisy LLM output.
    Tries:  (1) direct parse  (2) markdown fence  (3) first-{ to last-}
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Markdown code fence
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Outermost braces
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            pass

    return None


# ---- Ollama HTTP call -------------------------------------------------------

def query_ollama(prompt: str,
                 model: str = DEFAULT_MODEL,
                 retries: int = 2) -> Optional[str]:
    """
    POST the prompt to Ollama and return the raw response text.
    Retries up to `retries` times on failure.
    """
    payload = {"model": model, "prompt": prompt, "stream": False}

    for attempt in range(1, retries + 1):
        try:
            print(f"[ollama] request -> {model} (attempt {attempt}/{retries}) ...")
            resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            body = resp.json().get("response", "")
            if not body.strip():
                print("[ollama] WARNING: empty response")
                continue
            print(f"[ollama] received {len(body)} chars")
            return body

        except requests.exceptions.ConnectionError:
            print(f"[ollama] ERROR: cannot reach Ollama at {OLLAMA_URL}")
            print("[ollama] start it with: ollama serve")
        except requests.exceptions.Timeout:
            print(f"[ollama] ERROR: timed out after {TIMEOUT}s")
        except requests.exceptions.RequestException as exc:
            print(f"[ollama] ERROR: {exc}")

        if attempt < retries:
            print("[ollama] retrying ...")

    return None


# ---- high-level API ---------------------------------------------------------

def generate_openapi(source_code: str,
                     routes: List[Dict[str, Any]],
                     models: List[Dict[str, Any]],
                     model: str = DEFAULT_MODEL) -> Optional[Dict[str, Any]]:
    """
    End-to-end: build prompt -> call Ollama -> extract JSON -> return spec dict.
    """
    prompt = build_prompt(source_code, format_routes(routes), format_models(models))
    raw = query_ollama(prompt, model=model)
    if raw is None:
        return None

    spec = extract_json(raw)
    if spec is None:
        print("[ollama] could not parse JSON from response; first 400 chars:")
        print(raw[:400])
        return None

    print("[ollama] valid JSON extracted")
    return spec


# ---- self-test --------------------------------------------------------------

if __name__ == "__main__":
    print("Testing Ollama connectivity ...")
    r = query_ollama("Say hello in one word.", retries=1)
    print(f"Response: {r.strip()}" if r else "Ollama unreachable.")
