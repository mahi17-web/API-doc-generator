# API Documentation & SDK Generator

Automatically generate **OpenAPI specifications** and **client SDKs** from your backend source code using a local LLM (Ollama).

## How It Works

```
Backend Code  →  Parser  →  Ollama LLM  →  OpenAPI Spec  →  SDK Generator
  (FastAPI)      (regex)    (llama3)       (api.json)      (Python, JS)
```

1. **Parser** reads your backend file and extracts routes, models, and docstrings
2. **Ollama LLM** analyzes the code and generates a full OpenAPI 3.0.3 specification
3. **Spec Generator** validates and saves the JSON to `spec/api.json`
4. **SDK Generator** uses `openapi-generator-cli` to produce Python and JavaScript SDKs
5. **File Watcher** monitors your backend files and regenerates automatically on change

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Ollama

Make sure Ollama is running with a model pulled:

```bash
ollama serve          # Start the Ollama server (if not running)
ollama pull llama3    # Download the llama3 model (~4.7 GB)
```

### 3. Run the Generator

```bash
# One-shot: generate spec + SDKs from the sample backend
python main.py

# Or specify your own backend file and model
python main.py generate --file your_app.py --model llama3
```

## Commands

| Command    | Description                              |
|------------|------------------------------------------|
| `generate` | One-shot: parse → spec → SDK (default)   |
| `watch`    | Watch files and auto-regenerate on save  |
| `parse`    | Parse only — inspect extracted routes    |
| `spec`     | Generate OpenAPI spec only (no SDK)      |
| `sdk`      | Generate SDKs from an existing spec file |

### Examples

```bash
python main.py                              # Default one-shot generate
python main.py generate --file myapp.py     # Custom backend file
python main.py generate --model mistral     # Use a different Ollama model
python main.py watch                        # Watch mode (auto-regenerate)
python main.py parse                        # Inspect extracted routes/models
python main.py spec                         # Generate spec only
python main.py sdk --spec spec/api.json     # SDKs from existing spec
```

## Project Structure

```
api-doc-generator/
├── main.py              # Orchestrator — CLI entry point
├── parser.py            # Reads backend code, extracts routes & models
├── ollama_api.py        # Sends prompts to Ollama, extracts JSON
├── generator.py         # Builds, validates, and saves OpenAPI spec
├── sdk_generator.py     # Generates Python/JS SDKs via openapi-generator
├── watcher.py           # Watches files for changes, triggers regeneration
├── sample_backend.py    # Sample FastAPI bookstore API (test input)
├── requirements.txt     # Python dependencies
├── spec/                # Generated OpenAPI specs go here
│   └── api.json         # Latest generated spec
└── sdk/                 # Generated SDKs go here
    ├── python/
    └── javascript/
```

## SDK Generation (Optional)

SDK generation requires `openapi-generator-cli`. Install one of:

```bash
# Option 1: npm (recommended)
npm install @openapitools/openapi-generator-cli -g

# Option 2: Docker
docker pull openapitools/openapi-generator-cli
```

If not installed, the spec is still generated — you can generate SDKs later manually.

## Supported Frameworks

| Framework | Status        |
|-----------|---------------|
| FastAPI   | ✅ Supported  |
| Flask     | 🔜 Planned   |
| Express   | 🔜 Planned   |

## Requirements

- Python 3.10+
- Ollama running locally (`http://localhost:11434`)
- An Ollama model pulled (e.g., `llama3`, `mistral`, `codellama`)
