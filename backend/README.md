# API Documentation & SDK Generator — Backend

Production-quality FastAPI service that generates OpenAPI specs and client SDKs from backend source code using a local Ollama LLM.

## Architecture

```
backend/
  app/
    main.py              # FastAPI entry + lifespan (watcher startup/shutdown)
    core/
      config.py          # Typed settings (pydantic-settings, env overridable)
      logger.py          # Centralised logging
    api/
      routes.py          # POST /generate-docs, GET /health
    services/
      parser_service.py  # Regex-based route/model extraction
      ollama_service.py  # LLM prompt building, HTTP calls, retry
      openapi_service.py # Spec validation, backup, save pipeline
      sdk_service.py     # openapi-generator-cli auto-detect + execution
      watcher_service.py # Background file monitor with debounce
    models/
      request_models.py  # Pydantic request schemas
      response_models.py # Pydantic response schemas
    utils/
      file_utils.py      # Safe read/write/backup helpers
      json_validator.py  # JSON extraction + OpenAPI validation
  sample_backend/
    app.py               # Test FastAPI bookstore
  spec/                  # Generated OpenAPI specs
  sdk/                   # Generated client SDKs
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ensure Ollama is running
ollama serve
ollama pull llama3

# 3. Start the server
uvicorn app.main:app --reload

# 4. Generate documentation
curl -X POST http://localhost:8000/generate-docs \
  -H "Content-Type: application/json" \
  -d '{"file_path": "sample_backend/app.py"}'
```

## API Endpoints

| Method | Path             | Description                        |
|--------|------------------|------------------------------------|
| GET    | /health          | Health check                       |
| POST   | /generate-docs   | Trigger full pipeline              |
| GET    | /docs            | Swagger UI (auto-generated)        |
| GET    | /redoc           | ReDoc (auto-generated)             |

## Configuration

All settings can be overridden via environment variables with the `APIDOC_` prefix:

| Variable                  | Default                                    |
|---------------------------|--------------------------------------------|
| APIDOC_OLLAMA_URL         | http://localhost:11434/api/generate         |
| APIDOC_OLLAMA_MODEL       | llama3                                     |
| APIDOC_OLLAMA_TIMEOUT     | 300                                        |
| APIDOC_OLLAMA_RETRIES     | 2                                          |
| APIDOC_SPEC_FILE          | spec/api.json                              |
| APIDOC_SDK_LANGUAGES      | ["python", "javascript"]                   |
| APIDOC_WATCHER_DEBOUNCE   | 3.0                                        |

## Features

- **Auto-watch**: File watcher starts automatically with the server
- **Spec backup**: Timestamped backups before every overwrite
- **Validation**: Invalid LLM output is rejected; existing spec preserved
- **Retry**: Ollama calls retry automatically on failure
- **SDK auto-detect**: Finds npm / npx / docker for openapi-generator-cli
